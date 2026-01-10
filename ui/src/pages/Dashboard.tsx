/**
 * Overview Page (Dashboard)
 *
 * High-level system health and activity at-a-glance:
 * - Total runs, success rate, decisions, quality signals
 * - Recent activity
 * - Top decision types
 * - Quality signal health
 * - System alerts (drift events)
 */

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  ListChecks,
  Sparkles,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { PageHeader } from "../components/PageHeader";
import {
  StatCardSkeleton,
  TableSkeleton,
} from "../components/ui/LoadingSkeleton";
import { ErrorEmptyState, NoDataEmptyState } from "../components/ui/EmptyState";
import { API_CONFIG, API_ENDPOINTS } from "../config/api";
import { apiGet } from "../lib/apiClient";
import { useErrorHandler } from "../hooks/useErrorHandler";
import { safePercent, safeToFixed } from "../utils/safemath";

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
  decisions?: Array<{
    decision_type: string;
    selected: string;
  }>;
  quality_signals?: Array<{
    value: boolean;
  }>;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const { handleError } = useErrorHandler();

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const statsResponse = await apiGet<Stats>(
        API_ENDPOINTS.RUN_STATS,
        API_CONFIG.QUERY_API_BASE_URL
      );
      setStats(statsResponse);

      const runsResponse = await apiGet<RecentRun[]>(
        `${API_ENDPOINTS.RUNS}?page_size=100`,
        API_CONFIG.QUERY_API_BASE_URL
      );
      setRecentRuns(runsResponse);
      setLastUpdated(new Date());
    } catch (err) {
      const appError = handleError(err, "Dashboard.fetchDashboardData");
      setError(appError.message);
    } finally {
      setLoading(false);
    }
  };

  const formatLatency = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const decisionStats = useMemo(() => {
    let totalDecisions = 0;
    const typeCount: Record<string, number> = {};

    recentRuns.forEach((run) => {
      const decisions = Array.isArray(run.decisions) ? run.decisions : [];
      if (decisions.length > 0) {
        totalDecisions += decisions.length;
        decisions.forEach((decision) => {
          typeCount[decision.decision_type] =
            (typeCount[decision.decision_type] || 0) + 1;
        });
      }
    });

    return {
      total: totalDecisions,
      typeCount,
    };
  }, [recentRuns]);

  const qualitySignalStats = useMemo(() => {
    let totalSignals = 0;
    let positiveSignals = 0;
    let negativeSignals = 0;

    recentRuns.forEach((run) => {
      const signals = Array.isArray(run.quality_signals)
        ? run.quality_signals
        : [];
      if (signals.length > 0) {
        totalSignals += signals.length;
        signals.forEach((signal) => {
          if (signal.value) {
            positiveSignals++;
          } else {
            negativeSignals++;
          }
        });
      }
    });

    return {
      total: totalSignals,
      positive: positiveSignals,
      negative: negativeSignals,
    };
  }, [recentRuns]);

  const topDecisionTypes = useMemo(() => {
    return Object.entries(decisionStats.typeCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [decisionStats]);

  if (loading && !stats) {
    return (
      <div className="container mx-auto px-4 py-10 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton rows={6} />
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="container mx-auto px-4 py-10">
        <ErrorEmptyState message={error} onRetry={fetchDashboardData} />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-10">
      <PageHeader
        title="Overview"
        description="A high-level view of observed agent execution patterns, decisions, and signals within the selected scope."
        lastUpdated={lastUpdated}
        onRefresh={fetchDashboardData}
        loading={loading}
      />

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Total Runs</p>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">
            {stats?.total_runs || 0}
          </p>
          <p className="text-xs text-gray-500 mt-1">All agent executions</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Success Rate</p>
            {(stats?.success_rate || 0) >= 90 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <p className="text-3xl font-semibold text-gray-900">
            {safeToFixed(stats?.success_rate ?? 0, 1, "0.0")}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {(stats?.total_runs || 0) - (stats?.total_failures || 0)} successful
          </p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Active Decisions</p>
            <ListChecks className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">
            {decisionStats.total}
          </p>
          <p className="text-xs text-gray-500 mt-1">Total decisions tracked</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Quality Signals</p>
            <Sparkles className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">
            {qualitySignalStats.total}
          </p>
          <p className="text-xs text-gray-500 mt-1">Total signals recorded</p>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Recent Activity
              </h2>
              <p className="text-sm text-gray-500">
                Latest runs across all agents
              </p>
            </div>
            <Button variant="ghost" onClick={() => navigate("/runs")}>
              View all
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
          {recentRuns.length > 0 ? (
            <div className="space-y-3">
              {recentRuns.slice(0, 6).map((run) => (
                <button
                  key={run.run_id}
                  onClick={() => navigate(`/runs/${run.run_id}`)}
                  className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      {run.status === "success" ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-red-500" />
                      )}
                      <span className="text-sm font-medium text-gray-900">
                        {run.agent_id}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(run.started_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>
                      {Array.isArray(run.steps) ? run.steps.length : 0} steps
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <NoDataEmptyState entityName="recent runs" />
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Top Decision Types
              </h2>
              <p className="text-sm text-gray-500">
                Most common decision patterns
              </p>
            </div>
            <Button variant="ghost" onClick={() => navigate("/decisions")}>
              View all
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
          {topDecisionTypes.length > 0 ? (
            <div className="space-y-4">
              {topDecisionTypes.map(([type, count]) => {
                const percent = Math.round(
                  safePercent(count, decisionStats.total)
                );
                return (
                  <div key={type}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        {type}
                      </span>
                      <span className="text-sm text-gray-700">
                        {count} / {percent}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full">
                      <div
                        className="h-2 bg-purple-500 rounded-full"
                        style={{ width: `${percent}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <NoDataEmptyState entityName="decision data" />
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Quality Signal Health
              </h2>
              <p className="text-sm text-gray-500">Signal distribution</p>
            </div>
            <Button variant="ghost" onClick={() => navigate("/signals")}>
              View all
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
          {qualitySignalStats.total > 0 ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-green-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      Positive Signals
                    </p>
                    <p className="text-xs text-gray-500">Value = true</p>
                  </div>
                </div>
                <p className="text-2xl font-semibold text-green-600">
                  {qualitySignalStats.positive}
                </p>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-6 h-6 text-red-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      Negative Signals
                    </p>
                    <p className="text-xs text-gray-500">Value = false</p>
                  </div>
                </div>
                <p className="text-2xl font-semibold text-red-600">
                  {qualitySignalStats.negative}
                </p>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full flex">
                  <div
                    className="h-full bg-green-500"
                    style={{
                      width: `${safePercent(
                        qualitySignalStats.positive,
                        qualitySignalStats.total
                      )}%`,
                    }}
                  ></div>
                  <div
                    className="h-full bg-red-500"
                    style={{
                      width: `${safePercent(
                        qualitySignalStats.negative,
                        qualitySignalStats.total
                      )}%`,
                    }}
                  ></div>
                </div>
              </div>
            </div>
          ) : (
            <NoDataEmptyState entityName="signal data" />
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                System Status
              </h2>
              <p className="text-sm text-gray-500">Overall system health</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-900">
                    System Operational
                  </p>
                  <p className="text-xs text-green-600">All services running</p>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Success Rate</p>
                <p className="text-xl font-semibold text-gray-900">
                  {safeToFixed(stats?.success_rate ?? 0, 1, "0.0")}%
                </p>
              </div>
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Avg Latency</p>
                <p className="text-xl font-semibold text-gray-900">
                  {formatLatency(stats?.avg_latency_ms || 0)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
