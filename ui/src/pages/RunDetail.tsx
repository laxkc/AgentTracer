/**
 * RunDetail Page
 *
 * Displays complete details for a single agent run:
 * - Run metadata (agent_id, version, status, timing)
 * - Step timeline with latency visualization
 * - Failure analysis (if applicable)
 * - Navigation back to run list
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Calendar,
  CheckCircle,
  AlertCircle,
  Activity,
  Layers,
  GitBranch,
  Zap,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import TraceTimeline from '../components/TraceTimeline';
import FailureBreakdown from '../components/FailureBreakdown';
import DecisionsList from '../components/DecisionsList';
import QualitySignalsList from '../components/QualitySignalsList';
import { CardSkeleton, TableSkeleton } from '../components/ui/LoadingSkeleton';
import { ErrorEmptyState } from '../components/ui/EmptyState';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet } from '../lib/apiClient';
import { useErrorHandler } from '../hooks/useErrorHandler';

interface AgentRun {
  run_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  status: 'success' | 'failure' | 'partial';
  started_at: string;
  ended_at: string | null;
  created_at: string;
  steps: any[];
  failures: any[];
  decisions?: any[];
  quality_signals?: any[];
}

const RunDetail: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { handleError } = useErrorHandler();

  useEffect(() => {
    fetchRunDetails();
  }, [runId]);

  const fetchRunDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiGet<AgentRun>(
        API_ENDPOINTS.RUN_DETAIL(runId ?? ''),
        API_CONFIG.QUERY_API_BASE_URL
      );
      setRun(response);
    } catch (error) {
      const appError = handleError(error, 'RunDetail.fetchRunDetails');
      setError(appError.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (started: string, ended: string | null) => {
    if (!ended) return 'Running...';

    const start = new Date(started);
    const end = new Date(ended);
    const durationMs = end.getTime() - start.getTime();

    if (durationMs < 1000) return `${durationMs}ms`;
    if (durationMs < 60000) return `${(durationMs / 1000).toFixed(2)}s`;
    return `${(durationMs / 60000).toFixed(2)}m`;
  };

  const formatTimestamp = (timestamp: string) => new Date(timestamp).toLocaleString();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-50 text-green-700 border-green-200';
      case 'failure':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'partial':
        return 'bg-yellow-50 text-yellow-700 border-yellow-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failure':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />;
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-10 space-y-6">
        <CardSkeleton />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <TableSkeleton rows={4} />
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="container mx-auto px-4 py-10">
        <Button onClick={() => navigate('/runs')} variant="ghost" className="mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Runs
        </Button>
        <ErrorEmptyState message={error || 'Run not found'} onRetry={fetchRunDetails} />
      </div>
    );
  }

  const safeSteps = Array.isArray(run.steps) ? run.steps : [];
  const safeFailures = Array.isArray(run.failures) ? run.failures : [];
  const safeDecisions = Array.isArray(run.decisions) ? run.decisions : [];
  const safeSignals = Array.isArray(run.quality_signals) ? run.quality_signals : [];

  return (
    <div className="container mx-auto px-4 py-10">
      <Button onClick={() => navigate('/runs')} variant="ghost" className="mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Runs
      </Button>

      <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h1 className="text-2xl font-semibold text-gray-900">{run.agent_id}</h1>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold border ${getStatusColor(
                  run.status
                )}`}
              >
                {run.status}
              </span>
              {((run.decisions && run.decisions.length > 0) ||
                (run.quality_signals && run.quality_signals.length > 0)) && (
                <span className="px-2 py-1 bg-gray-100 text-gray-700 border border-gray-200 rounded text-xs font-semibold">
                  Extended Data
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">Version {run.agent_version}</p>
          </div>
          {getStatusIcon(run.status)}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <Activity className="w-4 h-4 text-blue-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Environment</p>
              <p className="text-sm font-semibold text-gray-900">{run.environment}</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <Calendar className="w-4 h-4 text-purple-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Started</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatTimestamp(run.started_at)}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <Clock className="w-4 h-4 text-green-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Duration</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatDuration(run.started_at, run.ended_at)}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
            <Layers className="w-4 h-4 text-orange-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Steps</p>
              <p className="text-sm font-semibold text-gray-900">{run.steps.length}</p>
            </div>
          </div>

          {run.decisions && run.decisions.length > 0 && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
              <GitBranch className="w-4 h-4 text-gray-700 mt-0.5" />
              <div>
                <p className="text-xs text-gray-600 font-medium">Decisions</p>
                <p className="text-sm font-semibold text-gray-900">{run.decisions.length}</p>
              </div>
            </div>
          )}

          {run.quality_signals && run.quality_signals.length > 0 && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
              <Zap className="w-4 h-4 text-gray-700 mt-0.5" />
              <div>
                <p className="text-xs text-gray-600 font-medium">Quality Signals</p>
                <p className="text-sm font-semibold text-gray-900">
                  {run.quality_signals.length}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-600">
            <span className="font-medium">Run ID:</span>{' '}
            <code className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
              {run.run_id}
            </code>
          </p>
        </div>
      </section>

      {run.failures && run.failures.length > 0 && (
        <div className="mb-6">
          <FailureBreakdown failures={safeFailures} steps={safeSteps} runStatus={run.status} />
        </div>
      )}

      {run.decisions && run.decisions.length > 0 && (
        <div className="mb-6">
          <DecisionsList decisions={safeDecisions} />
        </div>
      )}

      {run.quality_signals && run.quality_signals.length > 0 && (
        <div className="mb-6">
          <QualitySignalsList signals={safeSignals} />
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <TraceTimeline steps={safeSteps} runStarted={run.started_at} runEnded={run.ended_at} />
      </div>
    </div>
  );
};

export default RunDetail;
