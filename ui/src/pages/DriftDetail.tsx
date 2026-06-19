/**
 * Drift Detail Page
 *
 * Detailed view of a single drift event showing baseline vs observed comparison
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, TrendingUp, TrendingDown, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet, apiPost } from '../lib/apiClient';

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
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    if (driftId) {
      fetchDriftDetails();
    }
  }, [driftId]);

  const fetchDriftDetails = async () => {
    if (!driftId) return;

    try {
      setLoading(true);
      setError(null);

      const driftEvent = await apiGet<BehaviorDrift>(
        API_ENDPOINTS.DRIFT_DETAIL(driftId),
        API_CONFIG.QUERY_API_BASE_URL
      );
      setDrift(driftEvent);

      try {
        const baselineData = await apiGet<BehaviorBaseline>(
          API_ENDPOINTS.BASELINE_DETAIL(driftEvent.baseline_id),
          API_CONFIG.QUERY_API_BASE_URL
        );
        setBaseline(baselineData);
      } catch (err) {
        setBaseline(null);
      }

      setLoading(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch drift details');
      setLoading(false);
    }
  };

  const handleResolveDrift = async () => {
    if (!drift || drift.resolved_at || !driftId) {
      return;
    }

    try {
      setResolving(true);
      const resolvedDrift = await apiPost<BehaviorDrift>(
        API_ENDPOINTS.DRIFT_RESOLVE(driftId),
        undefined,
        API_CONFIG.QUERY_API_BASE_URL
      );
      setDrift(resolvedDrift);
      toast.success('Drift event marked as resolved');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to resolve drift');
    } finally {
      setResolving(false);
    }
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
          <Link to="/behaviors" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const changeVerb = drift.delta > 0 ? 'increased' : 'decreased';
  const TrendIcon = drift.delta > 0 ? TrendingUp : TrendingDown;

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
        <h1 className="text-3xl font-semibold text-gray-900 mt-3">Drift event details</h1>
        <p className="text-gray-600 mt-2">Detailed view of detected behavioral change.</p>
      </div>

      <section className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={getSeverityVariant(drift.severity)}>{drift.severity}</Badge>
              <Badge variant="secondary">{drift.drift_type}</Badge>
              {drift.resolved_at && (
                <Badge variant="success">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Resolved
                </Badge>
              )}
            </div>
            <div className="text-lg font-semibold text-gray-900">{drift.metric}</div>
            <div className="text-sm text-gray-600">
              {drift.agent_id} v{drift.agent_version} ({drift.environment})
            </div>
          </div>
          <div className="text-sm text-gray-500">
            Detected {new Date(drift.detected_at).toLocaleString()}
          </div>
        </div>

        <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-start gap-3">
          <TrendIcon className="h-5 w-5 text-gray-600 mt-0.5" />
          <div>
            <div className="text-sm font-medium text-gray-700 mb-1">Observed change</div>
            <p className="text-sm text-gray-900">
              The metric <span className="font-semibold">{drift.metric}</span> {changeVerb} from{' '}
              <span className="font-semibold">{(drift.baseline_value * 100).toFixed(2)}%</span> to{' '}
              <span className="font-semibold">{(drift.observed_value * 100).toFixed(2)}%</span>, a{' '}
              <span className="font-semibold">{drift.delta_percent > 0 ? '+' : ''}{drift.delta_percent.toFixed(1)}%</span> change.
            </p>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900">Baseline value</h2>
          <p className="text-4xl font-semibold text-gray-900 mt-4">
            {(drift.baseline_value * 100).toFixed(1)}%
          </p>
          <p className="text-sm text-gray-600 mt-2">Expected behavior</p>
          {baseline && (
            <div className="pt-4 mt-4 border-t border-gray-200 space-y-2 text-sm text-gray-600">
              <div className="flex items-center justify-between">
                <span>Baseline type</span>
                <span className="text-gray-900 font-medium">{baseline.baseline_type}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Created</span>
                <span className="text-gray-900 font-medium">
                  {new Date(baseline.created_at).toLocaleDateString()}
                </span>
              </div>
              {baseline.approved_by && (
                <div className="flex items-center justify-between">
                  <span>Approved by</span>
                  <span className="text-gray-900 font-medium">{baseline.approved_by}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900">Observed value</h2>
          <p className="text-4xl font-semibold text-gray-900 mt-4">
            {(drift.observed_value * 100).toFixed(1)}%
          </p>
          <p className="text-sm text-gray-600 mt-2">Current behavior</p>
          <div className="pt-4 mt-4 border-t border-gray-200 space-y-2 text-sm text-gray-600">
            <div className="flex items-center justify-between">
              <span>Window start</span>
              <span className="text-gray-900 font-medium">
                {new Date(drift.observation_window_start).toLocaleDateString()}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Window end</span>
              <span className="text-gray-900 font-medium">
                {new Date(drift.observation_window_end).toLocaleDateString()}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Sample size</span>
              <span className="text-gray-900 font-medium">
                {drift.observation_sample_size} runs
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900">Statistical analysis</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div>
            <dt className="text-sm font-medium text-gray-600">Test method</dt>
            <dd className="text-sm text-gray-900">{drift.test_method}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Significance</dt>
            <dd className="text-sm text-gray-900">p = {drift.significance.toFixed(4)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Absolute change</dt>
            <dd className="text-sm text-gray-900">
              {drift.delta > 0 ? '+' : ''}{(drift.delta * 100).toFixed(2)}%
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Relative change</dt>
            <dd className="text-sm text-gray-900">
              {drift.delta_percent > 0 ? '+' : ''}{drift.delta_percent.toFixed(1)}%
            </dd>
          </div>
        </dl>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900">Context</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div>
            <dt className="text-sm font-medium text-gray-600">Drift ID</dt>
            <dd className="text-sm text-gray-900 font-mono">{drift.drift_id}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Baseline ID</dt>
            <dd className="text-sm text-gray-900 font-mono">{drift.baseline_id}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Drift type</dt>
            <dd className="text-sm text-gray-900">{drift.drift_type}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Severity</dt>
            <dd className="text-sm text-gray-900">{drift.severity}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Created</dt>
            <dd className="text-sm text-gray-900">
              {new Date(drift.created_at).toLocaleString()}
            </dd>
          </div>
          {drift.resolved_at && (
            <div>
              <dt className="text-sm font-medium text-gray-600">Resolved</dt>
              <dd className="text-sm text-gray-900">
                {new Date(drift.resolved_at).toLocaleString()}
              </dd>
            </div>
          )}
        </dl>
      </section>

      <section className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <p className="text-sm text-gray-700">
          <strong>Interpretation:</strong> Drift is observational. Review changes in context to decide
          if investigation is needed.
        </p>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900">Related</h2>
        <div className="flex flex-wrap gap-2 mt-4">
          <Link
            to={`/drift/timeline?agent_id=${drift.agent_id}&agent_version=${drift.agent_version}&environment=${drift.environment}`}
          >
            <Button variant="outline" size="sm">
              View timeline
            </Button>
          </Link>
          <Link to="/drift/compare">
            <Button variant="outline" size="sm">Compare events</Button>
          </Link>
          <Link to="/behaviors">
            <Button variant="outline" size="sm">Back to dashboard</Button>
          </Link>
        </div>
      </section>

      {!drift.resolved_at && (
        <div className="flex gap-4">
          <Button onClick={handleResolveDrift} disabled={resolving}>
            <CheckCircle2 className="h-4 w-4 mr-2" />
            {resolving ? 'Resolving...' : 'Mark as resolved'}
          </Button>
        </div>
      )}
    </div>
  );
};

export default DriftDetail;
