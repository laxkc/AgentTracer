/**
 * Phase 3 - Drift Comparison Page
 *
 * Compare multiple drift events or baselines side-by-side.
 * Helps identify patterns and relationships between drift events.
 *
 * Design Constraints:
 * - Observational language only
 * - No quality judgments
 * - Drift is descriptive, not evaluative
 */

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  GitCompare,
  TrendingUp,
  TrendingDown,
  ExternalLink,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";

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
      const selected = driftEvents.filter((d) => selectedDrifts.includes(d.drift_id));
      setComparisonData(selected);
    } else {
      setComparisonData([]);
    }
  }, [selectedDrifts, driftEvents]);

  const fetchDriftEvents = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:8001/v1/phase3/drift?limit=1000");
      const data = await response.json();

      // Sort by detected_at descending
      data.sort(
        (a: BehaviorDrift, b: BehaviorDrift) =>
          new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      );

      setDriftEvents(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch drift events");
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
      case "low":
        return "secondary";
      case "medium":
        return "default";
      case "high":
        return "destructive";
      default:
        return "secondary";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
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
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Page Header - SINGLE INSTANCE */}
      <div className="space-y-1">
        <Link
          to="/behaviors"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium mb-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Behavior Dashboard
        </Link>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <GitCompare className="h-6 w-6 text-purple-600" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Drift Comparison</h1>
        </div>
        <p className="text-gray-500">
          Compare multiple drift events side-by-side to identify patterns
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Drift Selection Panel */}
        <div className="lg:col-span-1">
          <Card className="sticky top-4">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Select Drift Events</span>
                <Badge variant="secondary">{selectedDrifts.length} selected</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedDrifts.length > 0 && (
                <Button
                  onClick={() => setSelectedDrifts([])}
                  variant="outline"
                  size="sm"
                  className="w-full mb-4"
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Clear Selection
                </Button>
              )}

              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {driftEvents.map((drift) => {
                  const isSelected = selectedDrifts.includes(drift.drift_id);
                  return (
                    <div
                      key={drift.drift_id}
                      onClick={() => toggleDriftSelection(drift.drift_id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-blue-50 border-blue-300"
                          : "bg-gray-50 border-gray-200 hover:border-gray-300"
                      }`}
                    >
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
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Comparison View */}
        <div className="lg:col-span-2">
          {comparisonData.length === 0 ? (
            <Card className="p-12 text-center">
              <GitCompare className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 mb-2">Select drift events from the list to compare</p>
              <p className="text-sm text-gray-400">
                Select up to 5 drift events for side-by-side comparison
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <GitCompare className="h-5 w-5 text-gray-600" />
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900">
                        Comparison ({comparisonData.length} events)
                      </h2>
                      <p className="text-sm text-gray-600">
                        Comparing {comparisonData.length} drift event
                        {comparisonData.length !== 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {comparisonData.map((drift) => {
                const TrendIcon = drift.delta > 0 ? TrendingUp : TrendingDown;
                return (
                  <Card key={drift.drift_id}>
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant={getSeverityVariant(drift.severity)}>
                              {drift.severity}
                            </Badge>
                            <Badge variant="secondary">{drift.drift_type}</Badge>
                          </div>
                          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                            <TrendIcon className="h-5 w-5" />
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
                        <div className="bg-gray-50 rounded-lg p-4">
                          <div className="text-xs text-gray-600 mb-1">Baseline Value</div>
                          <div className="text-2xl font-bold text-gray-900">
                            {(drift.baseline_value * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-4">
                          <div className="text-xs text-gray-600 mb-1">Observed Value</div>
                          <div className="text-2xl font-bold text-gray-900">
                            {(drift.observed_value * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-1">
                          <div className="text-xs text-gray-600">Change</div>
                          <div className="text-sm font-medium text-gray-900">
                            {drift.delta_percent > 0 ? "+" : ""}
                            {drift.delta_percent.toFixed(1)}%
                          </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-xs text-gray-600">Significance</div>
                          <div className="text-sm font-medium text-gray-900">
                            p = {drift.significance.toFixed(4)}
                          </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-xs text-gray-600">Detected</div>
                          <div className="text-sm font-medium text-gray-900">
                            {new Date(drift.detected_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Info Note */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <p className="text-sm text-blue-800">
            <strong>About comparison:</strong> Comparing drift events helps identify patterns and
            relationships. Look for common metrics, similar severity levels, or temporal clustering
            to understand behavioral changes better.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default DriftComparison;
