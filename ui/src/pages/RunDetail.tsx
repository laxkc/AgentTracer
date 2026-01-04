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
import axios from 'axios';
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

const QUERY_API_URL = 'http://localhost:8001';

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
  // Phase 2: Optional decision and quality signal data
  decisions?: any[];
  quality_signals?: any[];
}

const RunDetail: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRunDetails();
  }, [runId]);

  const fetchRunDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${QUERY_API_URL}/v1/runs/${runId}`);
      setRun(response.data);
    } catch (err) {
      setError('Failed to fetch run details. Please check if the Query API is running.');
      console.error('Error fetching run:', err);
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

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'failure':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'partial':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failure':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading run details...</p>
        </div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Button
          onClick={() => navigate('/runs')}
          variant="ghost"
          className="mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Runs
        </Button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-800 mb-2 text-center">Error</h2>
          <p className="text-red-600 text-center">{error || 'Run not found'}</p>
          <Button
            onClick={fetchRunDetails}
            variant="destructive"
            className="mt-4 w-full"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back Button */}
      <Button
        onClick={() => navigate('/runs')}
        variant="ghost"
        className="mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Runs
      </Button>

      {/* Run Header */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900">{run.agent_id}</h1>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold border ${getStatusColor(
                  run.status
                )}`}
              >
                {run.status}
              </span>
              {((run.decisions && run.decisions.length > 0) ||
                (run.quality_signals && run.quality_signals.length > 0)) && (
                <span className="px-2 py-1 bg-purple-100 text-purple-700 border border-purple-300 rounded text-xs font-semibold">
                  Phase 2 Data
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">Version {run.agent_version}</p>
          </div>
          {getStatusIcon(run.status)}
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <Activity className="w-5 h-5 text-blue-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Environment</p>
              <p className="text-sm font-semibold text-gray-900">{run.environment}</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <Calendar className="w-5 h-5 text-purple-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Started</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatTimestamp(run.started_at)}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <Clock className="w-5 h-5 text-green-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Duration</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatDuration(run.started_at, run.ended_at)}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <Layers className="w-5 h-5 text-orange-500 mt-0.5" />
            <div>
              <p className="text-xs text-gray-600 font-medium">Steps</p>
              <p className="text-sm font-semibold text-gray-900">{run.steps.length}</p>
            </div>
          </div>

          {/* Phase 2: Decisions */}
          {run.decisions && run.decisions.length > 0 && (
            <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
              <GitBranch className="w-5 h-5 text-purple-600 mt-0.5" />
              <div>
                <p className="text-xs text-purple-700 font-medium">Decisions</p>
                <p className="text-sm font-semibold text-purple-900">{run.decisions.length}</p>
              </div>
            </div>
          )}

          {/* Phase 2: Quality Signals */}
          {run.quality_signals && run.quality_signals.length > 0 && (
            <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
              <Zap className="w-5 h-5 text-purple-600 mt-0.5" />
              <div>
                <p className="text-xs text-purple-700 font-medium">Quality Signals</p>
                <p className="text-sm font-semibold text-purple-900">{run.quality_signals.length}</p>
              </div>
            </div>
          )}
        </div>

        {/* Run ID */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-600">
            <span className="font-medium">Run ID:</span>{' '}
            <code className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
              {run.run_id}
            </code>
          </p>
        </div>
      </div>

      {/* Failure Breakdown (if failures exist) */}
      {run.failures && run.failures.length > 0 && (
        <div className="mb-6">
          <FailureBreakdown
            failures={run.failures}
            steps={run.steps}
            runStatus={run.status}
          />
        </div>
      )}

      {/* Phase 2: Agent Decisions */}
      {run.decisions && run.decisions.length > 0 && (
        <div className="mb-6">
          <DecisionsList decisions={run.decisions} />
        </div>
      )}

      {/* Phase 2: Quality Signals */}
      {run.quality_signals && run.quality_signals.length > 0 && (
        <div className="mb-6">
          <QualitySignalsList signals={run.quality_signals} />
        </div>
      )}

      {/* Step Timeline */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <TraceTimeline
          steps={run.steps}
          runStarted={run.started_at}
          runEnded={run.ended_at}
        />
      </div>
    </div>
  );
};

export default RunDetail;
