/**
 * Phase 3 - Baseline Manager
 *
 * Manage behavioral baselines for drift detection.
 * View, activate, and deactivate baselines.
 *
 * Design Constraints:
 * - Baselines are immutable (cannot edit after creation)
 * - Only one active baseline per (agent, version, environment)
 * - Privacy-safe descriptions only
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface BehaviorBaseline {
  baseline_id: string;
  profile_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_type: string;
  approved_by: string | null;
  approved_at: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

interface BehaviorProfile {
  profile_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  window_start: string;
  window_end: string;
  sample_size: number;
  decision_distributions: Record<string, Record<string, number>>;
  signal_distributions: Record<string, Record<string, number>>;
  latency_stats: Record<string, number>;
  created_at: string;
}

const BaselineManager: React.FC = () => {
  const [baselines, setBaselines] = useState<BehaviorBaseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Selected baseline for viewing details
  const [selectedBaseline, setSelectedBaseline] = useState<BehaviorBaseline | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<BehaviorProfile | null>(null);

  useEffect(() => {
    fetchBaselines();
  }, []);

  const fetchBaselines = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('http://localhost:8001/v1/phase3/baselines?limit=1000');
      const data = await response.json();

      // Sort by created_at descending
      data.sort(
        (a: BehaviorBaseline, b: BehaviorBaseline) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setBaselines(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch baselines');
      setLoading(false);
    }
  };

  const fetchProfileDetails = async (profileId: string) => {
    try {
      const response = await fetch(`http://localhost:8001/v1/phase3/profiles/${profileId}`);
      const data = await response.json();
      setSelectedProfile(data);
    } catch (err) {
      console.error('Failed to fetch profile details:', err);
      setSelectedProfile(null);
    }
  };

  const handleViewBaseline = (baseline: BehaviorBaseline) => {
    setSelectedBaseline(baseline);
    fetchProfileDetails(baseline.profile_id);
  };

  const closeModal = () => {
    setSelectedBaseline(null);
    setSelectedProfile(null);
  };

  // Get unique environments and types
  const environments = Array.from(new Set(baselines.map((b) => b.environment)));
  const types = Array.from(new Set(baselines.map((b) => b.baseline_type)));

  // Apply filters
  const filteredBaselines = baselines.filter((baseline) => {
    if (environmentFilter !== 'all' && baseline.environment !== environmentFilter) return false;
    if (typeFilter !== 'all' && baseline.baseline_type !== typeFilter) return false;
    if (statusFilter === 'active' && !baseline.is_active) return false;
    if (statusFilter === 'inactive' && baseline.is_active) return false;
    return true;
  });

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'version':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'time_window':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'manual':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading baselines...</p>
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
            onClick={fetchBaselines}
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
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Baseline Manager</h1>
        <p className="text-gray-600">
          View and manage behavioral baselines for drift detection
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <div className="text-sm font-medium text-gray-600">Total Baselines</div>
          <div className="text-3xl font-bold text-gray-900 mt-2">{baselines.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <div className="text-sm font-medium text-gray-600">Active Baselines</div>
          <div className="text-3xl font-bold text-gray-900 mt-2">
            {baselines.filter((b) => b.is_active).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <div className="text-sm font-medium text-gray-600">Agents Covered</div>
          <div className="text-3xl font-bold text-gray-900 mt-2">
            {new Set(baselines.map((b) => b.agent_id)).size}
          </div>
        </div>
      </div>

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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Types</option>
              {types.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>
          </div>

          <div className="ml-auto">
            <button
              onClick={fetchBaselines}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Baselines Table */}
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
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Approval
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredBaselines.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                  No baselines match the current filters
                </td>
              </tr>
            ) : (
              filteredBaselines.map((baseline) => (
                <tr key={baseline.baseline_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{baseline.agent_id}</div>
                    <div className="text-xs text-gray-500">v{baseline.agent_version}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-800">
                      {baseline.environment}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded border ${getTypeColor(
                        baseline.baseline_type
                      )}`}
                    >
                      {baseline.baseline_type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {baseline.is_active ? (
                      <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800 border border-green-200">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {baseline.approved_by ? (
                      <div className="text-sm">
                        <div className="text-green-600 font-medium">✓ Approved</div>
                        <div className="text-xs text-gray-500">{baseline.approved_by}</div>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">Not approved</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {new Date(baseline.created_at).toLocaleDateString()}
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(baseline.created_at).toLocaleTimeString()}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleViewBaseline(baseline)}
                      className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Details Modal */}
      {selectedBaseline && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Baseline Details</h2>
                <p className="text-sm text-gray-600 mt-1">
                  {selectedBaseline.agent_id} v{selectedBaseline.agent_version} ({selectedBaseline.environment})
                </p>
              </div>
              <button
                onClick={closeModal}
                className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Baseline Info */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Baseline Information</h3>
                <dl className="grid grid-cols-2 gap-4">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Baseline ID</dt>
                    <dd className="text-sm text-gray-900 font-mono">{selectedBaseline.baseline_id}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Profile ID</dt>
                    <dd className="text-sm text-gray-900 font-mono">{selectedBaseline.profile_id}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Type</dt>
                    <dd className="text-sm text-gray-900">{selectedBaseline.baseline_type}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Status</dt>
                    <dd className="text-sm text-gray-900">
                      {selectedBaseline.is_active ? 'Active' : 'Inactive'}
                    </dd>
                  </div>
                  {selectedBaseline.description && (
                    <div className="col-span-2">
                      <dt className="text-sm font-medium text-gray-500">Description</dt>
                      <dd className="text-sm text-gray-900">{selectedBaseline.description}</dd>
                    </div>
                  )}
                </dl>
              </div>

              {/* Profile Data */}
              {selectedProfile && (
                <>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">
                      Behavior Profile Data
                    </h3>
                    <div className="space-y-4">
                      <div>
                        <div className="text-sm font-medium text-gray-700">Time Window</div>
                        <div className="text-sm text-gray-900">
                          {new Date(selectedProfile.window_start).toLocaleString()} →{' '}
                          {new Date(selectedProfile.window_end).toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500">
                          Sample size: {selectedProfile.sample_size} runs
                        </div>
                      </div>

                      {/* Decision Distributions */}
                      {Object.keys(selectedProfile.decision_distributions).length > 0 && (
                        <div>
                          <div className="text-sm font-medium text-gray-700 mb-2">
                            Decision Distributions
                          </div>
                          {Object.entries(selectedProfile.decision_distributions).map(
                            ([decisionType, distribution]) => (
                              <div key={decisionType} className="mb-3">
                                <div className="text-xs font-medium text-gray-600 mb-1">
                                  {decisionType}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(distribution).map(([option, probability]) => (
                                    <span
                                      key={option}
                                      className="px-2 py-1 text-xs bg-blue-50 text-blue-800 rounded border border-blue-200"
                                    >
                                      {option}: {(probability * 100).toFixed(1)}%
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      )}

                      {/* Signal Distributions */}
                      {Object.keys(selectedProfile.signal_distributions).length > 0 && (
                        <div>
                          <div className="text-sm font-medium text-gray-700 mb-2">
                            Quality Signal Distributions
                          </div>
                          {Object.entries(selectedProfile.signal_distributions).map(
                            ([signalType, distribution]) => (
                              <div key={signalType} className="mb-3">
                                <div className="text-xs font-medium text-gray-600 mb-1">
                                  {signalType}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(distribution).map(([code, probability]) => (
                                    <span
                                      key={code}
                                      className="px-2 py-1 text-xs bg-green-50 text-green-800 rounded border border-green-200"
                                    >
                                      {code}: {(probability * 100).toFixed(1)}%
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      )}

                      {/* Latency Stats */}
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">
                          Latency Statistics
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(selectedProfile.latency_stats).map(([stat, value]) => (
                            <div key={stat} className="flex justify-between">
                              <span className="text-xs text-gray-600">{stat}:</span>
                              <span className="text-xs font-medium text-gray-900">
                                {typeof value === 'number' ? value.toFixed(2) : value}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={closeModal}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Info Note */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>About baselines:</strong> Baselines are immutable snapshots of expected agent
          behavior. They serve as reference points for drift detection. Only one baseline can be
          active per agent/version/environment at a time.
        </p>
      </div>
    </div>
  );
};

export default BaselineManager;
