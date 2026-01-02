/**
 * DecisionsList Component
 *
 * Displays Phase 2 agent decisions in a clear, structured format.
 * Shows decision points, options considered, selection, and reasoning.
 *
 * Design Principles (Phase 2):
 * - Observational language only ("correlated with", "associated with")
 * - No judgment of correctness
 * - Neutral tone throughout
 */

import React from 'react';
import { GitBranch, CheckCircle, Gauge } from 'lucide-react';

interface AgentDecision {
  decision_id: string;
  run_id: string;
  step_id: string | null;
  decision_type: string;
  selected: string;
  reason_code: string;
  confidence: number | null;
  metadata: Record<string, any>;
  recorded_at: string;
  created_at: string;
}

interface DecisionsListProps {
  decisions: AgentDecision[];
}

const DecisionsList: React.FC<DecisionsListProps> = ({ decisions }) => {
  if (!decisions || decisions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-blue-500" />
          Agent Decisions
        </h2>
        <p className="text-gray-500 text-center py-8">
          No decision points recorded for this run
        </p>
        <p className="text-gray-400 text-sm text-center">
          Phase 2 decision tracking was not enabled or no decisions were made
        </p>
      </div>
    );
  }

  const formatDecisionType = (type: string): string => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatReasonCode = (code: string): string => {
    return code.replace(/_/g, ' ');
  };

  const getDecisionTypeColor = (type: string): string => {
    switch (type) {
      case 'tool_selection':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'retrieval_strategy':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'response_mode':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'retry_strategy':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'orchestration_path':
        return 'bg-pink-100 text-pink-800 border-pink-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getConfidenceColor = (confidence: number | null): string => {
    if (confidence === null) return 'text-gray-400';
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.5) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const formatConfidence = (confidence: number | null): string => {
    if (confidence === null) return 'N/A';
    return `${(confidence * 100).toFixed(0)}%`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <GitBranch className="w-5 h-5 text-blue-500" />
        Agent Decisions
        <span className="ml-auto text-sm font-normal text-gray-500">
          {decisions.length} {decisions.length === 1 ? 'decision' : 'decisions'}
        </span>
      </h2>

      <div className="space-y-4">
        {decisions.map((decision, index) => (
          <div
            key={decision.decision_id}
            className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-gray-500 font-medium text-sm">#{index + 1}</span>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold border ${getDecisionTypeColor(
                    decision.decision_type
                  )}`}
                >
                  {formatDecisionType(decision.decision_type)}
                </span>
              </div>
              {decision.confidence !== null && (
                <div className="flex items-center gap-1">
                  <Gauge className="w-4 h-4 text-gray-400" />
                  <span className={`text-sm font-semibold ${getConfidenceColor(decision.confidence)}`}>
                    {formatConfidence(decision.confidence)}
                  </span>
                </div>
              )}
            </div>

            {/* Selection */}
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium text-gray-600">Selected:</span>
                <span className="text-sm font-bold text-gray-900">{decision.selected}</span>
              </div>
              <div className="ml-6 text-sm text-gray-600">
                <span className="font-medium">Reason:</span>{' '}
                <span className="italic">{formatReasonCode(decision.reason_code)}</span>
              </div>
            </div>

            {/* Candidates (if present) */}
            {decision.metadata.candidates && decision.metadata.candidates.length > 0 && (
              <div className="mb-3 ml-6">
                <span className="text-xs font-medium text-gray-500">Options considered:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {decision.metadata.candidates.map((candidate: string, idx: number) => (
                    <span
                      key={idx}
                      className={`px-2 py-0.5 rounded text-xs border ${
                        candidate === decision.selected
                          ? 'bg-green-50 text-green-700 border-green-300 font-semibold'
                          : 'bg-gray-50 text-gray-600 border-gray-200'
                      }`}
                    >
                      {candidate}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Additional Metadata */}
            {Object.keys(decision.metadata).filter((key) => key !== 'candidates').length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <span className="text-xs font-medium text-gray-500">Additional context:</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {Object.entries(decision.metadata)
                    .filter(([key]) => key !== 'candidates')
                    .map(([key, value]) => (
                      <span key={key} className="text-xs bg-gray-50 px-2 py-1 rounded border border-gray-200">
                        <span className="font-medium text-gray-700">{key}:</span>{' '}
                        <span className="text-gray-600">{JSON.stringify(value)}</span>
                      </span>
                    ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer Note */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 italic">
          Phase 2 Observability: Decision data is observational only and does not reflect correctness or
          quality judgments. These records describe agent behavior patterns.
        </p>
      </div>
    </div>
  );
};

export default DecisionsList;
