/**
 * Phase 3 - Behavior Dashboard
 *
 * Overview of all agents and their behavioral stability.
 * Shows active baselines and recent drift events.
 *
 * Design Constraints:
 * - Observational language only (no judgmental terms)
 * - No health scores or rankings
 * - Drift is descriptive, not evaluative
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface BehaviorBaseline {
  baseline_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_type: string;
  is_active: boolean;
  created_at: string;
}

interface BehaviorDrift {
  drift_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  drift_type: string;
  metric: string;
  severity: string;
  detected_at: string;
  resolved_at: string | null;
}

interface DriftSummary {
  total_drift_events: number;
  unresolved_drift_events: number;
  drift_by_severity: Record<string, number>;
  drift_by_type: Record<string, number>;
  agents_with_drift: number;
}

interface AgentRow {
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline: BehaviorBaseline | null;
  drift_count: number;
  unresolved_drift: number;
  latest_drift: BehaviorDrift | null;
}

const BehaviorDashboard: React.FC = () => {
  const [baselines, setBaselines] = useState<BehaviorBaseline[]>([]);
  const [driftEvents, setDriftEvents] = useState<BehaviorDrift[]>([]);
  const [summary, setSummary] = useState<DriftSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
  const [showOnlyDrift, setShowOnlyDrift] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch active baselines
      const baselinesRes = await fetch('http://localhost:8001/v1/phase3/baselines?is_active=true&limit=1000');
      const baselinesData = await baselinesRes.json();
      setBaselines(baselinesData);

      // Fetch recent drift (last 7 days, unresolved)
      const driftRes = await fetch('http://localhost:8001/v1/phase3/drift?resolved=false&limit=1000');
      const driftData = await driftRes.json();
      setDriftEvents(driftData);

      // Fetch summary
      const summaryRes = await fetch('http://localhost:8001/v1/phase3/drift/summary?days=7');
      const summaryData = await summaryRes.json();
      setSummary(summaryData);

      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      setLoading(false);
    }
  };

  // Group data by agent
  const agentRows: AgentRow[] = React.useMemo(() => {
    const agentMap = new Map<string, AgentRow>();

    // Add baselines
    baselines.forEach((baseline) => {
      const key = `${baseline.agent_id}|${baseline.agent_version}|${baseline.environment}`;
      if (!agentMap.has(key)) {
        agentMap.set(key, {
          agent_id: baseline.agent_id,
          agent_version: baseline.agent_version,
          environment: baseline.environment,
          baseline: baseline,
          drift_count: 0,
          unresolved_drift: 0,
          latest_drift: null,
        });
      }
    });

    // Add drift counts
    driftEvents.forEach((drift) => {
      const key = `${drift.agent_id}|${drift.agent_version}|${drift.environment}`;
      let row = agentMap.get(key);

      if (!row) {
        // Agent has drift but no baseline
        row = {
          agent_id: drift.agent_id,
          agent_version: drift.agent_version,
          environment: drift.environment,
          baseline: null,
          drift_count: 0,
          unresolved_drift: 0,
          latest_drift: null,
        };
        agentMap.set(key, row);
      }

      row.drift_count++;
      if (!drift.resolved_at) {
        row.unresolved_drift++;
      }

      // Track latest drift
      if (!row.latest_drift || new Date(drift.detected_at) > new Date(row.latest_drift.detected_at)) {
        row.latest_drift = drift;
      }
    });

    return Array.from(agentMap.values());
  }, [baselines, driftEvents]);

  // Apply filters
  const filteredRows = agentRows.filter((row) => {
    if (environmentFilter !== 'all' && row.environment !== environmentFilter) {
      return false;
    }
    if (showOnlyDrift && row.unresolved_drift === 0) {
      return false;
    }
    return true;
  });

  // Get unique environments
  const environments = Array.from(new Set(agentRows.map((r) => r.environment)));

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading behavior data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600">Error: {error}</p>
          <button
            onClick={fetchData}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
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
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Behavior Dashboard</h1>
        <p className="text-gray-600">
          Observational view of agent behavioral stability and detected changes
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
            <div className="text-sm font-medium text-gray-600">Agents Monitored</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{agentRows.length}</div>
            <div className="text-xs text-gray-500 mt-1">with active baselines</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
            <div className="text-sm font-medium text-gray-600">Unresolved Drift</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{summary.unresolved_drift_events}</div>
            <div className="text-xs text-gray-500 mt-1">changes detected</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
            <div className="text-sm font-medium text-gray-600">Drift Events (7d)</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{summary.total_drift_events}</div>
            <div className="text-xs text-gray-500 mt-1">total detected</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
            <div className="text-sm font-medium text-gray-600">Agents with Drift</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{summary.agents_with_drift}</div>
            <div className="text-xs text-gray-500 mt-1">observing changes</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 border border-gray-200">
        <div className="flex flex-wrap gap-4 items-center">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Environment</label>
            <select
              value={environmentFilter}
              onChange={(e) => setEnvironmentFilter(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Environments</option>
              {environments.map((env) => (
                <option key={env} value={env}>
                  {env}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="showOnlyDrift"
              checked={showOnlyDrift}
              onChange={(e) => setShowOnlyDrift(e.target.checked)}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="showOnlyDrift" className="ml-2 text-sm text-gray-700">
              Show only agents with unresolved drift
            </label>
          </div>

          <div className="ml-auto">
            <button
              onClick={fetchData}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Agent Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Agent
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Environment
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Baseline
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Drift Detected
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Latest Change
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  No agents match the current filters
                </td>
              </tr>
            ) : (
              filteredRows.map((row) => (
                <tr key={`${row.agent_id}|${row.agent_version}|${row.environment}`} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{row.agent_id}</div>
                    <div className="text-xs text-gray-500">v{row.agent_version}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-800">
                      {row.environment}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {row.baseline ? (
                      <div className="text-sm">
                        <div className="text-green-600 font-medium">Active</div>
                        <div className="text-xs text-gray-500">{row.baseline.baseline_type}</div>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">No baseline</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {row.unresolved_drift > 0 ? (
                      <div className="text-sm">
                        <div className="font-medium text-gray-900">{row.unresolved_drift} unresolved</div>
                        <div className="text-xs text-gray-500">{row.drift_count} total</div>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">No drift</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {row.latest_drift ? (
                      <div className="text-sm">
                        <span
                          className={`inline-block px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(
                            row.latest_drift.severity
                          )}`}
                        >
                          {row.latest_drift.severity}
                        </span>
                        <div className="text-xs text-gray-500 mt-1">
                          {new Date(row.latest_drift.detected_at).toLocaleDateString()}
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      {row.latest_drift && (
                        <Link
                          to={`/drift/${row.latest_drift.drift_id}`}
                          className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
                        >
                          View Drift
                        </Link>
                      )}
                      <Link
                        to={`/drift/timeline?agent_id=${row.agent_id}&agent_version=${row.agent_version}&environment=${row.environment}`}
                        className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
                      >
                        Timeline
                        </Link>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Info Note */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> Drift indicates that agent behavior has changed relative to the baseline.
          Drift is observational - it describes change, not quality. Human interpretation is required
          to determine if action is needed.
        </p>
      </div>
    </div>
  );
};

export default BehaviorDashboard;
