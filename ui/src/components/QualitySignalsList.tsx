/**
 * QualitySignalsList Component
 *
 * Displays Phase 2 quality signals - atomic, observable indicators correlated with outcomes.
 * Shows signal types, codes, values, and contextual metadata.
 *
 * Design Principles (Phase 2):
 * - Neutral, observational language ("observed", "correlated with")
 * - No quality scores or correctness judgments
 * - Factual presentation only
 */

import React from 'react';
import { Activity, CheckCircle, XCircle, AlertTriangle, Zap, Timer, Database } from 'lucide-react';

interface AgentQualitySignal {
  signal_id: string;
  run_id: string;
  step_id: string | null;
  signal_type: string;
  signal_code: string;
  value: boolean;
  weight: number | null;
  metadata: Record<string, any>;
  recorded_at: string;
  created_at: string;
}

interface QualitySignalsListProps {
  signals: AgentQualitySignal[];
}

const QualitySignalsList: React.FC<QualitySignalsListProps> = ({ signals }) => {
  if (!signals || signals.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-purple-500" />
          Quality Signals
        </h2>
        <p className="text-gray-500 text-center py-8">
          No quality signals recorded for this run
        </p>
        <p className="text-gray-400 text-sm text-center">
          Phase 2 signal tracking was not enabled or no signals were observed
        </p>
      </div>
    );
  }

  const formatSignalType = (type: string): string => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatSignalCode = (code: string): string => {
    return code.replace(/_/g, ' ');
  };

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'schema_valid':
        return <CheckCircle className="w-4 h-4" />;
      case 'empty_retrieval':
        return <Database className="w-4 h-4" />;
      case 'tool_success':
        return <CheckCircle className="w-4 h-4" />;
      case 'tool_failure':
        return <XCircle className="w-4 h-4" />;
      case 'retry_occurred':
        return <AlertTriangle className="w-4 h-4" />;
      case 'latency_threshold':
        return <Timer className="w-4 h-4" />;
      case 'token_usage':
        return <Zap className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  const getSignalTypeColor = (type: string): string => {
    switch (type) {
      case 'schema_valid':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'empty_retrieval':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'tool_success':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'tool_failure':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'retry_occurred':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'latency_threshold':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'token_usage':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getValueBadge = (value: boolean) => {
    if (value) {
      return (
        <span className="px-2 py-0.5 bg-green-100 text-green-700 border border-green-300 rounded text-xs font-semibold">
          TRUE
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 bg-gray-100 text-gray-700 border border-gray-300 rounded text-xs font-semibold">
        FALSE
      </span>
    );
  };

  // Group signals by type for better visualization
  const groupedSignals = signals.reduce((acc, signal) => {
    const type = signal.signal_type;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(signal);
    return acc;
  }, {} as Record<string, AgentQualitySignal[]>);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Activity className="w-5 h-5 text-purple-500" />
        Quality Signals
        <span className="ml-auto text-sm font-normal text-gray-500">
          {signals.length} {signals.length === 1 ? 'signal' : 'signals'}
        </span>
      </h2>

      <div className="space-y-6">
        {Object.entries(groupedSignals).map(([type, typeSignals]) => (
          <div key={type} className="border border-gray-200 rounded-lg p-4">
            {/* Type Header */}
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
              <span className={`p-1.5 rounded ${getSignalTypeColor(type)}`}>
                {getSignalIcon(type)}
              </span>
              <span className="font-semibold text-gray-900">{formatSignalType(type)}</span>
              <span className="ml-auto text-xs text-gray-500">
                {typeSignals.length} {typeSignals.length === 1 ? 'occurrence' : 'occurrences'}
              </span>
            </div>

            {/* Signals of this type */}
            <div className="space-y-2">
              {typeSignals.map((signal) => (
                <div
                  key={signal.signal_id}
                  className="bg-gray-50 rounded p-3 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-700">
                        {formatSignalCode(signal.signal_code)}
                      </span>
                      {getValueBadge(signal.value)}
                    </div>
                    {signal.weight !== null && (
                      <span className="text-xs text-gray-500">
                        weight: <span className="font-semibold">{signal.weight.toFixed(2)}</span>
                      </span>
                    )}
                  </div>

                  {/* Metadata */}
                  {Object.keys(signal.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {Object.entries(signal.metadata).map(([key, value]) => (
                        <span
                          key={key}
                          className="text-xs bg-white px-2 py-1 rounded border border-gray-200"
                        >
                          <span className="font-medium text-gray-700">{key}:</span>{' '}
                          <span className="text-gray-600">{JSON.stringify(value)}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">{Object.keys(groupedSignals).length}</p>
          <p className="text-xs text-gray-600">Signal Types</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">{signals.length}</p>
          <p className="text-xs text-gray-600">Total Signals</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-green-600">
            {signals.filter((s) => s.value === true).length}
          </p>
          <p className="text-xs text-gray-600">True Values</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-500">
            {signals.filter((s) => s.value === false).length}
          </p>
          <p className="text-xs text-gray-600">False Values</p>
        </div>
      </div>

      {/* Footer Note */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 italic">
          Phase 2 Observability: Quality signals are atomic, factual indicators correlated with agent
          outcomes. They do not represent quality scores or judgments of correctness.
        </p>
      </div>
    </div>
  );
};

export default QualitySignalsList;
