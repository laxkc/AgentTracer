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

import React, { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Select } from './ui/select';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet } from '../lib/apiClient';
import { Card, CardContent } from './ui/card';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from './ui/pagination';

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

interface DriftTimelinePoint {
  timestamp: string;
  metric: string;
  value: number;
  drift_detected: boolean;
  drift_id: string | null;
}

interface DriftTimelineResponse {
  agent_id: string;
  agent_version: string;
  environment: string;
  timeline: DriftTimelinePoint[];
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
  const [timelinePoints, setTimelinePoints] = useState<DriftTimelinePoint[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [showChart, setShowChart] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    fetchTimeline();
  }, [agentId, agentVersion, environment, startDate, endDate, days]);

  useEffect(() => {
    setPage(1);
  }, [agentId, agentVersion, environment, selectedType]);

  useEffect(() => {
    fetchDriftPage();
  }, [agentId, agentVersion, environment, selectedType, page]);

  const fetchTimeline = async () => {
    try {
      setChartLoading(true);
      setChartError(null);

      const params = new URLSearchParams({
        agent_id: agentId,
      });

      if (agentVersion) params.append('agent_version', agentVersion);
      if (environment) params.append('environment', environment);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (!startDate && !endDate && days) {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        params.append('start_date', cutoffDate.toISOString());
      }

      const response = await apiGet<DriftTimelineResponse>(
        `${API_ENDPOINTS.DRIFT_TIMELINE}?${params.toString()}`,
        API_CONFIG.QUERY_API_BASE_URL
      );

      setTimelinePoints(response.timeline || []);
    } catch (error) {
      setChartError(error instanceof Error ? error.message : 'Failed to fetch drift timeline');
    } finally {
      setChartLoading(false);
    }
  };

  const fetchDriftPage = async () => {
    try {
      setListLoading(true);
      setListError(null);

      const params = new URLSearchParams({
        agent_id: agentId,
        limit: pageSize.toString(),
        offset: ((page - 1) * pageSize).toString(),
      });

      if (agentVersion) params.append('agent_version', agentVersion);
      if (environment) params.append('environment', environment);
      if (selectedType !== 'all') params.append('drift_type', selectedType);

      const response = await apiGet<BehaviorDrift[]>(
        `${API_ENDPOINTS.DRIFT}?${params.toString()}`,
        API_CONFIG.QUERY_API_BASE_URL
      );

      setDriftEvents(response);
    } catch (error) {
      setListError(error instanceof Error ? error.message : 'Failed to fetch drift data');
    } finally {
      setListLoading(false);
    }
  };

  const uniqueMetrics = Array.from(new Set(timelinePoints.map((point) => point.metric)));
  const driftTypes = ['decision', 'signal', 'latency'];

  const filteredTimeline = selectedMetric === 'all'
    ? timelinePoints
    : timelinePoints.filter((point) => point.metric === selectedMetric);

  // Group events by date for timeline visualization
  const eventsByDate = driftEvents.reduce((acc, drift) => {
    const date = new Date(drift.detected_at).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(drift);
    return acc;
  }, {} as Record<string, BehaviorDrift[]>);

  // Prepare chart data - group by metric and date
  const chartData = useMemo(() => {
    const dataMap = new Map<string, { date: string; [key: string]: number | string }>();

    filteredTimeline.forEach((point) => {
      const date = new Date(point.timestamp).toLocaleDateString();
      const key = date;

      if (!dataMap.has(key)) {
        dataMap.set(key, { date });
      }

      const entry = dataMap.get(key)!;
      entry[point.metric] = point.value * 100; // Convert to percentage
    });

    return Array.from(dataMap.values()).sort((a, b) => 
      new Date(a.date as string).getTime() - new Date(b.date as string).getTime()
    );
  }, [filteredTimeline]);

  // Get unique metrics for chart lines
  const chartMetrics = Array.from(new Set(filteredTimeline.map((point) => point.metric))).slice(0, 5);

  const hasNextPage = driftEvents.length === pageSize;

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

  if (listLoading && driftEvents.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading drift timeline...</p>
        </div>
      </div>
    );
  }

  if (listError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {listError}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
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
              {driftTypes.map((type) => (
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

      {showChart && (
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Drift Over Time</h3>
          {chartLoading ? (
            <div className="text-center text-gray-500 py-12">Loading chart...</div>
          ) : chartError ? (
            <div className="text-center text-red-600 py-12">Error: {chartError}</div>
          ) : chartData.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No data available for chart</p>
          ) : (
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
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">Total Events</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{driftEvents.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">Unresolved</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {driftEvents.filter((d) => !d.resolved_at).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">High Severity</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {driftEvents.filter((d) => d.severity === 'high').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
          <div className="text-xs font-medium text-gray-600">Unique Metrics</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {new Set(driftEvents.map((d) => d.metric)).size}
          </div>
        </div>
      </div>

      {!showChart && driftEvents.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 border border-gray-200 text-center">
          <p className="text-gray-500">No drift events found for the selected filters</p>
        </div>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Drift Events (page {page})
              </h3>
            </CardContent>
          </Card>
          <div className="space-y-4">
            {Object.entries(eventsByDate).map(([date, events]) => (
              <div key={date} className="space-y-3">
                <div className="text-sm font-medium text-gray-700">{date}</div>
                <div className="space-y-3">
                  {events.map((drift) => (
                    <Card key={drift.drift_id} className="border-gray-200">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-start gap-4">
                            <div className="flex-shrink-0 mt-0.5">
                              <span
                                className={`inline-block px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(
                                  drift.severity
                                )}`}
                              >
                                {drift.severity}
                              </span>
                            </div>
                            <div className="space-y-1">
                              <div className="flex items-center gap-2 flex-wrap">
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
                              <div className="text-xs text-gray-500">
                                Statistical significance: p={drift.significance.toFixed(4)} •{' '}
                                Sample size: {drift.observation_sample_size} runs
                                {drift.resolved_at && (
                                  <span className="ml-2 text-green-600">• Resolved</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="text-xs text-gray-500 whitespace-nowrap">
                            {new Date(drift.detected_at).toLocaleTimeString()}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  disabled={page === 1 || listLoading}
                />
              </PaginationItem>
              <PaginationItem>
                <PaginationLink isActive>{page}</PaginationLink>
              </PaginationItem>
              <PaginationItem>
                <PaginationNext
                  onClick={() => setPage((prev) => prev + 1)}
                  disabled={!hasNextPage || listLoading}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
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
