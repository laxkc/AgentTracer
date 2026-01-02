/**
 * Dashboard Page
 *
 * Displays aggregated statistics and insights:
 * - Total runs, failures, success rate
 * - Failure type breakdown
 * - Step type distribution
 * - Recent activity
 * - Quick links to filtered views
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
} from 'lucide-react';

const QUERY_API_URL = 'http://localhost:8001';

interface Stats {
  total_runs: number;
  total_failures: number;
  success_rate: number;
  avg_latency_ms: number;
  failure_breakdown: Record<string, number>;
  step_type_breakdown: Record<string, number>;
}

interface RecentRun {
  run_id: string;
  agent_id: string;
  status: string;
  started_at: string;
  steps: any[];
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch stats
      const statsResponse = await axios.get(`${QUERY_API_URL}/v1/stats`);
      setStats(statsResponse.data);

      // Fetch recent runs
      const runsResponse = await axios.get(`${QUERY_API_URL}/v1/runs?page_size=5`);
      setRecentRuns(runsResponse.data);
    } catch (err) {
      setError('Failed to fetch dashboard data');
      console.error('Error fetching dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatLatency = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getFailureColor = (type: string) => {
    const colors: Record<string, string> = {
      tool: 'bg-red-100 text-red-700 border-red-200',
      model: 'bg-orange-100 text-orange-700 border-orange-200',
      retrieval: 'bg-blue-100 text-blue-700 border-blue-200',
      orchestration: 'bg-purple-100 text-purple-700 border-purple-200',
    };
    return colors[type] || 'bg-gray-100 text-gray-700 border-gray-200';
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-800 mb-2 text-center">Error</h2>
          <p className="text-red-600 text-center">{error}</p>
          <button
            onClick={fetchDashboardData}
            className="mt-4 w-full px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
        <p className="text-gray-600">
          Real-time AgentTracer metrics and insights
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-600">Total Runs</p>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats?.total_runs || 0}</p>
          <p className="text-xs text-gray-500 mt-1">All agent executions</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-600">Success Rate</p>
            {(stats?.success_rate || 0) >= 90 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {stats?.success_rate.toFixed(1) || 0}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            
            {stats?.total_runs - (stats?.total_failures || 0)} successful
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-600">Failures</p>
            <AlertTriangle className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats?.total_failures || 0}</p>
          <p className="text-xs text-gray-500 mt-1">Runs with failures</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-600">Avg Latency</p>
            <Clock className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {formatLatency(stats?.avg_latency_ms || 0)}
          </p>
          <p className="text-xs text-gray-500 mt-1">Per step average</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Failure Breakdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Failure Type Breakdown
          </h2>
          {stats?.failure_breakdown && Object.keys(stats.failure_breakdown).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stats.failure_breakdown).map(([type, count]) => {
                const [failureType, failureCode] = type.split('/');
                return (
                  <div key={type} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold border ${getFailureColor(
                          failureType
                        )}`}
                      >
                        {failureType}
                      </span>
                      <span className="text-sm text-gray-700 font-mono">
                        {failureCode}
                      </span>
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <p className="text-gray-600">No failures recorded</p>
            </div>
          )}
        </div>

        {/* Step Type Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Step Type Distribution
          </h2>
          {stats?.step_type_breakdown && Object.keys(stats.step_type_breakdown).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stats.step_type_breakdown).map(([type, count]) => (
                <div key={type}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 capitalize">
                      {type}
                    </span>
                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{
                        width: `${
                          (count /
                            Object.values(stats.step_type_breakdown).reduce(
                              (a, b) => a + b,
                              0
                            )) *
                          100
                        }%`,
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">No step data available</div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
          <button
            onClick={() => navigate('/runs')}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            View all
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {recentRuns.length > 0 ? (
          <div className="space-y-3">
            {recentRuns.map((run) => (
              <div
                key={run.run_id}
                onClick={() => navigate(`/runs/${run.run_id}`)}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  {run.status === 'success' ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">{run.agent_id}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(run.started_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">{run.steps.length} steps</span>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">No recent activity</div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
