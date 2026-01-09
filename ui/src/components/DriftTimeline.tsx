/**
 * Drift Timeline Component
 *
 * Visualizes drift events over time for a specific agent.
 * Shows behavioral changes in a timeline view with charts.
 *
 * Design Constraints:
 * - Observational language only
 * - No quality judgments
 * - Drift is descriptive, not evaluative
 */

import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Select } from './ui/select';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';

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

interface DriftTimelineProps {
  agentId: string;
  agentVersion?: string;
  environment?: string;
  startDate?: string;
  endDate?: string;
  days?: number;
}

const DriftTimeline: React.FC<DriftTimelineProps> = ({
  agentId,
  agentVersion,
  environment,
  startDate,
  endDate,
  days = 30,
}) => {
  const [driftEvents, setDriftEvents] = useState<BehaviorDrift[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [showChart, setShowChart] = useState(true);

  useEffect(() => {
    fetchDriftData();
  }, [agentId, agentVersion, environment, startDate, endDate]);

  const fetchDriftData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams({
        agent_id: agentId,
        limit: '1000',
      });

      if (agentVersion) params.append('agent_version', agentVersion);
      if (environment) params.append('environment', environment);

      const response = await fetch(`${API_CONFIG.QUERY_API_BASE_URL}${API_ENDPOINTS.DRIFT}?${params}`);
      const data = await response.json();

      // Filter by date range if specified
      let filteredData = data;
      if (startDate || endDate) {
        filteredData = data.filter((drift: BehaviorDrift) => {
          const detectedDate = new Date(drift.detected_at);
          if (startDate && detectedDate < new Date(startDate)) return false;
          if (endDate && detectedDate > new Date(endDate)) return false;
          return true;
        });
      } else {
        // Default: last N days
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        filteredData = data.filter((drift: BehaviorDrift) => {
          return new Date(drift.detected_at) >= cutoffDate;
        });
      }

      // Sort by detected_at descending
      filteredData.sort(
        (a: BehaviorDrift, b: BehaviorDrift) =>
          new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      );

      setDriftEvents(filteredData);
      setLoading(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch drift data');
      setLoading(false);
    }
  };

  // Get unique metrics and types
  const uniqueMetrics = Array.from(new Set(driftEvents.map((d) => d.metric)));
  const uniqueTypes = Array.from(new Set(driftEvents.map((d) => d.drift_type)));

  // Apply filters
  const filteredEvents = driftEvents.filter((drift) => {
    if (selectedMetric !== 'all' && drift.metric !== selectedMetric) return false;
    if (selectedType !== 'all' && drift.drift_type !== selectedType) return false;
    return true;
  });

  // Group events by date for timeline visualization
  const eventsByDate = filteredEvents.reduce((acc, drift) => {
    const date = new Date(drift.detected_at).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(drift);
    return acc;
  }, {} as Record<string, BehaviorDrift[]>);

  // Prepare chart data - group by metric and date
  const chartData = React.useMemo(() => {
    const dataMap = new Map<string, { date: string; [key: string]: number | string }>();

    filteredEvents.forEach((drift) => {
      const date = new Date(drift.detected_at).toLocaleDateString();
      const key = date;

      if (!dataMap.has(key)) {
        dataMap.set(key, { date });
      }

      const entry = dataMap.get(key)!;
      entry[drift.metric] = drift.observed_value * 100; // Convert to percentage
    });

    return Array.from(dataMap.values()).sort((a, b) => 
      new Date(a.date as string).getTime() - new Date(b.date as string).getTime()
    );
  }, [filteredEvents]);

  // Get unique metrics for chart lines
  const chartMetrics = Array.from(new Set(filteredEvents.map((d) => d.metric))).slice(0, 5); // Limit to 5 metrics for readability

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'decision':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'signal':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'latency':
        return 'bg-indigo-100 text-indigo-800 border-indigo-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading drift timeline...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Drift Timeline</h2>
        <p className="text-sm text-gray-600 mt-1">
          Chronological view of detected behavioral changes for {agentId}
          {agentVersion && ` v${agentVersion}`}
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Metric</label>
            <Select
              value={selectedMetric}
              onChange={(event) => setSelectedMetric(event.target.value)}
            >
              <option value="all">All Metrics</option>
              {uniqueMetrics.map((metric) => (
                <option key={metric} value={metric}>
                  {metric}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Drift Type</label>
            <Select
              value={selectedType}
              onChange={(event) => setSelectedType(event.target.value)}
            >
              <option value="all">All Types</option>
              {uniqueTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 border border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-700">Visualization</h3>
          <p className="text-xs text-gray-500">Toggle between chart and list view</p>
        </div>
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={showChart}
            onChange={(event) => setShowChart(event.target.checked)}
            className="sr-only"
          />
          <div className={`relative inline-block w-14 h-8 rounded-full transition-colors ${showChart ? 'bg-indigo-600' : 'bg-gray-300'}`}>
            <div className={`absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform ${showChart ? 'translate-x-6' : ''}`}></div>
          </div>
          <span className="ml-3 text-sm text-gray-700">{showChart ? 'Chart' : 'List'}</span>
        </label>
      </div>

      {showChart && chartData.length > 0 && (
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Drift Over Time</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                angle={-45}
                textAnchor="end"
                height={80}
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                label={{ value: 'Value (%)', angle: -90, position: 'insideLeft' }}
                tick={{ fontSize: 12 }}
              />
              <Tooltip 
                formatter={(value: number) => `${value.toFixed(2)}%`}
                labelStyle={{ color: '#374151' }}
              />
              <Legend />
              {chartMetrics.map((metric, index) => {
                const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'];
                return (
                  <Line
                    key={metric}
                    type="monotone"
                    dataKey={metric}
                    stroke={colors[index % colors.length]}
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    name={metric.length > 30 ? `${metric.substring(0, 30)}...` : metric}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
          {chartMetrics.length === 0 && (
            <p className="text-center text-gray-500 py-8">No data available for chart</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">Total Events</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{filteredEvents.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">Unresolved</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {filteredEvents.filter((d) => !d.resolved_at).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">High Severity</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {filteredEvents.filter((d) => d.severity === 'high').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">Unique Metrics</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {new Set(filteredEvents.map((d) => d.metric)).size}
          </div>
        </div>
      </div>

      {!showChart && filteredEvents.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 border border-gray-200 text-center">
          <p className="text-gray-500">No drift events found for the selected filters</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              Drift Events ({filteredEvents.length})
            </h3>
          </div>
          <div className="divide-y divide-gray-200">
            {Object.entries(eventsByDate).map(([date, events]) => (
              <div key={date} className="p-4">
                <div className="text-sm font-medium text-gray-700 mb-3">{date}</div>
                <div className="space-y-3">
                  {events.map((drift) => (
                    <div
                      key={drift.drift_id}
                      className="flex items-start gap-4 p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-indigo-300 transition-colors"
                    >
                      <div className="flex-shrink-0 mt-1">
                        <span
                          className={`inline-block px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(
                            drift.severity
                          )}`}
                        >
                          {drift.severity}
                        </span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span
                                className={`px-2 py-0.5 text-xs font-medium rounded border ${getTypeColor(
                                  drift.drift_type
                                )}`}
                              >
                                {drift.drift_type}
                              </span>
                              <span className="text-sm font-medium text-gray-900">{drift.metric}</span>
                            </div>
                            <div className="text-sm text-gray-700">
                              Observed{' '}
                              {drift.delta > 0 ? 'increase' : 'decrease'} from{' '}
                              <span className="font-medium">{(drift.baseline_value * 100).toFixed(1)}%</span>{' '}
                              to{' '}
                              <span className="font-medium">{(drift.observed_value * 100).toFixed(1)}%</span>
                              <span className="text-gray-600">
                                {' '}
                                ({drift.delta_percent > 0 ? '+' : ''}
                                {drift.delta_percent.toFixed(1)}%)
                              </span>
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              Statistical significance: p={drift.significance.toFixed(4)} •{' '}
                              Sample size: {drift.observation_sample_size} runs
                              {drift.resolved_at && (
                                <span className="ml-2 text-green-600">• Resolved</span>
                              )}
                            </div>
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(drift.detected_at).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Interpreting drift:</strong> Events shown here represent detected changes in agent
          behavior relative to the baseline. Drift is observational and does not indicate quality or
          correctness. Review context and decide if investigation is needed.
        </p>
      </div>
    </div>
  );
};

export default DriftTimeline;
