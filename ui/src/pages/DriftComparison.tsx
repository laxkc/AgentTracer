/**
 * Drift Comparison Page
 *
 * Compare multiple drift events side-by-side to identify patterns and relationships
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, TrendingUp, TrendingDown, ExternalLink, XCircle, GitCompare } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet } from '../lib/apiClient';

interface BehaviorDrift {
  drift_id: string;
  baseline_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  drift_type: string;
  metric: string;
  baseline_value: number;
  observed_value: number;
  delta: number;
  delta_percent: number;
  significance: number;
  test_method: string;
  severity: string;
  detected_at: string;
  observation_window_start: string;
  observation_window_end: string;
  observation_sample_size: number;
  resolved_at: string | null;
  created_at: string;
}

const DriftComparison: React.FC = () => {
  const [selectedDrifts, setSelectedDrifts] = useState<string[]>([]);
  const [driftEvents, setDriftEvents] = useState<BehaviorDrift[]>([]);
  const [comparisonData, setComparisonData] = useState<BehaviorDrift[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDriftEvents();
  }, []);

  useEffect(() => {
    if (selectedDrifts.length > 0) {
      const selected = driftEvents.filter((drift) => selectedDrifts.includes(drift.drift_id));
      setComparisonData(selected);
    } else {
      setComparisonData([]);
    }
  }, [selectedDrifts, driftEvents]);

  const fetchDriftEvents = async () => {
    try {
      setLoading(true);
      setError(null);

      const fetchedDrifts = await apiGet<BehaviorDrift[]>(
        `${API_ENDPOINTS.DRIFT}?limit=1000`,
        API_CONFIG.QUERY_API_BASE_URL
      );
      if (!Array.isArray(fetchedDrifts)) {
        throw new Error('Unexpected drift response');
      }

      fetchedDrifts.sort(
        (a: BehaviorDrift, b: BehaviorDrift) =>
          new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      );

      setDriftEvents(fetchedDrifts);
      setLoading(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch drift events');
      setLoading(false);
    }
  };

  const toggleDriftSelection = (driftId: string) => {
    setSelectedDrifts((prev) =>
      prev.includes(driftId) ? prev.filter((id) => id !== driftId) : [...prev, driftId]
    );
  };

  const getSeverityVariant = (severity: string) => {
    switch (severity) {
      case 'low':
        return 'secondary';
      case 'medium':
        return 'default';
      case 'high':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading drift events...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600">Error: {error}</p>
          <Button onClick={fetchDriftEvents} className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-10 space-y-6">
      <div>
        <Link
          to="/behaviors"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Behavior Dashboard
        </Link>
        <h1 className="text-3xl font-semibold text-gray-900 mt-3">Drift Comparisons</h1>
        <p className="text-gray-600 mt-2">
          Compare drift events to identify patterns
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card className="sticky top-4">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Select drift events</CardTitle>
                <Badge variant="secondary">{selectedDrifts.length} selected</Badge>
              </div>
              {selectedDrifts.length > 0 && (
                <Button
                  onClick={() => setSelectedDrifts([])}
                  variant="outline"
                  size="sm"
                  className="mt-3 w-full"
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Clear selection
                </Button>
              )}
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                {driftEvents.length === 0 ? (
                  <div className="text-center py-12">
                    <GitCompare className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600">No drift events found</p>
                    <p className="text-gray-500 text-sm mt-1">
                      Drift events will appear here when detected
                    </p>
                  </div>
                ) : (
                  driftEvents.map((drift) => {
                    const isSelected = selectedDrifts.includes(drift.drift_id);
                    return (
                      <Card
                        key={drift.drift_id}
                        onClick={() => toggleDriftSelection(drift.drift_id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'border-blue-300 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1 pr-2">
                              <div className="text-sm font-medium text-gray-900 truncate">
                                {drift.metric}
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {drift.agent_id} v{drift.agent_version}
                              </div>
                            </div>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {}}
                              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                          </div>
                          <div className="flex gap-2 flex-wrap">
                            <Badge variant={getSeverityVariant(drift.severity)} className="text-xs">
                              {drift.severity}
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                              {drift.drift_type}
                            </Badge>
                          </div>
                          <div className="text-xs text-gray-500 mt-2">
                            {new Date(drift.detected_at).toLocaleDateString()}
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {comparisonData.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
              <GitCompare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No drift events selected</h3>
              <p className="text-gray-600 mb-2">Select drift events from the left to compare them side-by-side</p>
              <p className="text-sm text-gray-500">
                You can select up to 5 drift events for comparison
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h2 className="text-lg font-semibold text-gray-900">
                  Comparison ({comparisonData.length} events)
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Comparing {comparisonData.length} drift event{comparisonData.length !== 1 ? 's' : ''}.
                </p>
              </div>

              {comparisonData.map((drift) => {
                const TrendIcon = drift.delta > 0 ? TrendingUp : TrendingDown;
                return (
                  <div key={drift.drift_id} className="bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant={getSeverityVariant(drift.severity)}>
                            {drift.severity}
                          </Badge>
                          <Badge variant="secondary">{drift.drift_type}</Badge>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                          <TrendIcon className="h-4 w-4" />
                          {drift.metric}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {drift.agent_id} v{drift.agent_version} ({drift.environment})
                        </p>
                      </div>
                      <Link to={`/drift/${drift.drift_id}`}>
                        <Button variant="outline" size="sm">
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Details
                        </Button>
                      </Link>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <div className="text-xs text-gray-600 mb-1">Baseline value</div>
                        <div className="text-2xl font-semibold text-gray-900">
                          {(drift.baseline_value * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <div className="text-xs text-gray-600 mb-1">Observed value</div>
                        <div className="text-2xl font-semibold text-gray-900">
                          {(drift.observed_value * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-xs text-gray-600">Change</div>
                        <div className="font-medium text-gray-900">
                          {drift.delta_percent > 0 ? '+' : ''}
                          {drift.delta_percent.toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-600">Significance</div>
                        <div className="font-medium text-gray-900">p = {drift.significance.toFixed(4)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-600">Detected</div>
                        <div className="font-medium text-gray-900">
                          {new Date(drift.detected_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <p className="text-sm text-gray-700">
          <strong>About comparison:</strong> Comparing drift events helps identify patterns and
          relationships. Look for common metrics, similar severity levels, or temporal clustering.
        </p>
      </div>
    </div>
  );
};

export default DriftComparison;
