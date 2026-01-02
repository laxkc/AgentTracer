/**
 * Phase 3 - Drift Detail Page
 *
 * Detailed view of a single drift event.
 * Shows baseline vs observed comparison and full context.
 *
 * Design Constraints:
 * - Observational language only
 * - No prescriptive actions or recommendations
 * - Drift is descriptive, not evaluative
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

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

const DriftDetail: React.FC = () => {
  const { driftId } = useParams<{ driftId: string }>();
  const [drift, setDrift] = useState<BehaviorDrift | null>(null);
  const [baseline, setBaseline] = useState<BehaviorBaseline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (driftId) {
      fetchDriftDetails();
    }
  }, [driftId]);

  const fetchDriftDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch drift event
      const driftRes = await fetch(`http://localhost:8001/v1/phase3/drift/${driftId}`);
      if (!driftRes.ok) {
        throw new Error('Drift event not found');
      }
      const driftData = await driftRes.json();
      setDrift(driftData);

      // Fetch baseline
      const baselineRes = await fetch(
        `http://localhost:8001/v1/phase3/baselines/${driftData.baseline_id}`
      );
      if (baselineRes.ok) {
        const baselineData = await baselineRes.json();
        setBaseline(baselineData);
      }

      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch drift details');
      setLoading(false);
    }
  };

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
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading drift details...</p>
        </div>
      </div>
    );
  }

  if (error || !drift) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600">Error: {error || 'Drift event not found'}</p>
          <Link to="/behavior" className="mt-4 inline-block text-indigo-600 hover:text-indigo-900">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const changeDirection = drift.delta > 0 ? 'increase' : 'decrease';
  const changeVerb = drift.delta > 0 ? 'increased' : 'decreased';

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <Link to="/behavior" className="text-indigo-600 hover:text-indigo-900 text-sm font-medium">
          ← Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mt-2">Drift Event Details</h1>
        <p className="text-gray-600 mt-1">Detailed view of detected behavioral change</p>
      </div>

      {/* Summary Card */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`px-3 py-1 text-sm font-medium rounded border ${getSeverityColor(
                  drift.severity
                )}`}
              >
                {drift.severity} severity
              </span>
              <span
                className={`px-3 py-1 text-sm font-medium rounded border ${getTypeColor(
                  drift.drift_type
                )}`}
              >
                {drift.drift_type} drift
              </span>
              {drift.resolved_at && (
                <span className="px-3 py-1 text-sm font-medium rounded border border-green-300 bg-green-100 text-green-800">
                  Resolved
                </span>
              )}
            </div>
            <div className="text-lg font-semibold text-gray-900">{drift.metric}</div>
            <div className="text-sm text-gray-600 mt-1">
              {drift.agent_id} v{drift.agent_version} ({drift.environment})
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-600">Detected</div>
            <div className="text-base font-medium text-gray-900">
              {new Date(drift.detected_at).toLocaleDateString()}
            </div>
            <div className="text-xs text-gray-500">
              {new Date(drift.detected_at).toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* Main Change Description */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <div className="text-sm font-medium text-gray-700 mb-2">Observed Change</div>
          <p className="text-base text-gray-900">
            The metric <span className="font-semibold">{drift.metric}</span> {changeVerb} from{' '}
            <span className="font-bold text-gray-900">
              {(drift.baseline_value * 100).toFixed(2)}%
            </span>{' '}
            to{' '}
            <span className="font-bold text-gray-900">
              {(drift.observed_value * 100).toFixed(2)}%
            </span>
            , representing a{' '}
            <span className="font-bold text-gray-900">
              {drift.delta_percent > 0 ? '+' : ''}
              {drift.delta_percent.toFixed(1)}%
            </span>{' '}
            change.
          </p>
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Baseline */}
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Baseline Value</h2>
          <div className="text-center">
            <div className="text-5xl font-bold text-gray-900 mb-2">
              {(drift.baseline_value * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600">Expected behavior</div>
          </div>
          {baseline && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="text-xs text-gray-600 space-y-1">
                <div>
                  <span className="font-medium">Baseline Type:</span> {baseline.baseline_type}
                </div>
                <div>
                  <span className="font-medium">Created:</span>{' '}
                  {new Date(baseline.created_at).toLocaleDateString()}
                </div>
                {baseline.approved_by && (
                  <div>
                    <span className="font-medium">Approved By:</span> {baseline.approved_by}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Observed */}
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Observed Value</h2>
          <div className="text-center">
            <div className="text-5xl font-bold text-gray-900 mb-2">
              {(drift.observed_value * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600">Current behavior</div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-xs text-gray-600 space-y-1">
              <div>
                <span className="font-medium">Window:</span>{' '}
                {new Date(drift.observation_window_start).toLocaleDateString()} -{' '}
                {new Date(drift.observation_window_end).toLocaleDateString()}
              </div>
              <div>
                <span className="font-medium">Sample Size:</span> {drift.observation_sample_size} runs
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Statistical Details */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Statistical Analysis</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-600">Test Method</dt>
            <dd className="text-sm text-gray-900 mt-1">{drift.test_method}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Statistical Significance</dt>
            <dd className="text-sm text-gray-900 mt-1">
              p = {drift.significance.toFixed(4)}
              {drift.significance < 0.05 && (
                <span className="ml-2 text-xs text-green-600">(p &lt; 0.05)</span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Absolute Change</dt>
            <dd className="text-sm text-gray-900 mt-1">
              {drift.delta > 0 ? '+' : ''}
              {(drift.delta * 100).toFixed(2)}%
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Relative Change</dt>
            <dd className="text-sm text-gray-900 mt-1">
              {drift.delta_percent > 0 ? '+' : ''}
              {drift.delta_percent.toFixed(1)}%
            </dd>
          </div>
        </dl>
      </div>

      {/* Context Information */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Context Information</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-600">Drift ID</dt>
            <dd className="text-sm text-gray-900 font-mono mt-1">{drift.drift_id}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Baseline ID</dt>
            <dd className="text-sm text-gray-900 font-mono mt-1">{drift.baseline_id}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Drift Type</dt>
            <dd className="text-sm text-gray-900 mt-1">{drift.drift_type}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Severity</dt>
            <dd className="text-sm text-gray-900 mt-1">{drift.severity}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Created At</dt>
            <dd className="text-sm text-gray-900 mt-1">
              {new Date(drift.created_at).toLocaleString()}
            </dd>
          </div>
          {drift.resolved_at && (
            <div>
              <dt className="text-sm font-medium text-gray-600">Resolved At</dt>
              <dd className="text-sm text-gray-900 mt-1">
                {new Date(drift.resolved_at).toLocaleString()}
              </dd>
            </div>
          )}
        </dl>
      </div>

      {/* Interpretation Guide */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-base font-semibold text-blue-900 mb-3">Interpreting This Drift Event</h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p>
            <strong>What this means:</strong> The agent's behavior has changed relative to the
            established baseline. Specifically, the distribution or value of{' '}
            <span className="font-medium">{drift.metric}</span> has shifted.
          </p>
          <p>
            <strong>What this does NOT mean:</strong> This drift detection does not indicate whether
            the change is good, bad, correct, or incorrect. Drift is purely observational.
          </p>
          <p>
            <strong>Next steps:</strong> Review the context of this change. Consider:
          </p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>Was there a recent deployment or configuration change?</li>
            <li>Is this change expected based on known system updates?</li>
            <li>Does the magnitude of change warrant investigation?</li>
            <li>Are there related drift events in other metrics?</li>
          </ul>
          <p className="mt-3">
            <strong>Remember:</strong> Human interpretation is required to determine if action is
            needed. The platform provides visibility, not decisions.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-6 flex gap-4">
        <Link
          to={`/drift/timeline?agent_id=${drift.agent_id}&agent_version=${drift.agent_version}&environment=${drift.environment}`}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          View Drift Timeline
        </Link>
        <Link
          to="/behavior"
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
};

export default DriftDetail;
