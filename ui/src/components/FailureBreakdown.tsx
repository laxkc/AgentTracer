/**
 * FailureBreakdown Component
 *
 * Displays failure analysis with semantic classification:
 * - Failure type breakdown (tool/model/retrieval/orchestration)
 * - Failure code distribution
 * - Step linkage
 * - Actionable insights
 *
 * This component helps answer "why did the agent fail?" (Phase-1 goal)
 */

import React from 'react';
import { AlertTriangle, AlertCircle, Database, Cpu, Link2 } from 'lucide-react';

interface Failure {
  failure_id: string;
  run_id: string;
  step_id: string | null;
  failure_type: 'tool' | 'model' | 'retrieval' | 'orchestration';
  failure_code: string;
  message: string;
  created_at: string;
}

interface Step {
  step_id: string;
  seq: number;
  name: string;
  step_type: string;
}

interface FailureBreakdownProps {
  failures: Failure[];
  steps: Step[];
  runStatus: 'success' | 'failure' | 'partial';
}

const FailureBreakdown: React.FC<FailureBreakdownProps> = ({
  failures,
  steps,
  runStatus,
}) => {
  const getFailureIcon = (type: string) => {
    switch (type) {
      case 'tool':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'model':
        return <Cpu className="w-5 h-5 text-orange-500" />;
      case 'retrieval':
        return <Database className="w-5 h-5 text-blue-500" />;
      case 'orchestration':
        return <AlertTriangle className="w-5 h-5 text-purple-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getFailureColor = (type: string) => {
    switch (type) {
      case 'tool':
        return 'border-red-300 bg-red-50';
      case 'model':
        return 'border-orange-300 bg-orange-50';
      case 'retrieval':
        return 'border-blue-300 bg-blue-50';
      case 'orchestration':
        return 'border-purple-300 bg-purple-50';
      default:
        return 'border-gray-300 bg-gray-50';
    }
  };

  const getFailureTextColor = (type: string) => {
    switch (type) {
      case 'tool':
        return 'text-red-800';
      case 'model':
        return 'text-orange-800';
      case 'retrieval':
        return 'text-blue-800';
      case 'orchestration':
        return 'text-purple-800';
      default:
        return 'text-gray-800';
    }
  };

  const getStepInfo = (stepId: string | null) => {
    if (!stepId) return null;
    return steps.find(s => s.step_id === stepId);
  };

  const getRecommendations = (failure: Failure) => {
    const recommendations: string[] = [];

    switch (failure.failure_type) {
      case 'tool':
        if (failure.failure_code === 'timeout') {
          recommendations.push('Consider increasing timeout threshold');
          recommendations.push('Check network connectivity and API health');
          recommendations.push('Implement exponential backoff for retries');
        } else if (failure.failure_code === 'schema_invalid') {
          recommendations.push('Validate tool output schema');
          recommendations.push('Update tool integration tests');
        }
        break;

      case 'model':
        recommendations.push('Check model endpoint availability');
        recommendations.push('Verify API key and quota limits');
        recommendations.push('Review prompt engineering');
        break;

      case 'retrieval':
        if (failure.failure_code === 'empty_retrieval') {
          recommendations.push('Expand knowledge base coverage');
          recommendations.push('Adjust retrieval similarity threshold');
          recommendations.push('Review query preprocessing');
        }
        break;

      case 'orchestration':
        recommendations.push('Check orchestration logic');
        recommendations.push('Review error handling');
        recommendations.push('Add defensive validation');
        break;
    }

    return recommendations;
  };

  if (runStatus === 'success' || failures.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-6 h-6 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-green-900 mb-1">
          No Failures Detected
        </h3>
        <p className="text-sm text-green-700">
          This run completed successfully without any failures.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-5 h-5 text-red-600" />
          <h3 className="text-lg font-semibold text-red-900">
            Failure Analysis
          </h3>
        </div>
        <p className="text-sm text-red-700">
          {failures.length} failure{failures.length > 1 ? 's' : ''} detected in this run
        </p>
      </div>

      {/* Failures List */}
      <div className="space-y-4">
        {failures.map((failure) => {
          const stepInfo = getStepInfo(failure.step_id);
          const recommendations = getRecommendations(failure);

          return (
            <div
              key={failure.failure_id}
              className={`border-2 rounded-lg overflow-hidden ${getFailureColor(
                failure.failure_type
              )}`}
            >
              {/* Failure Header */}
              <div className="p-4">
                <div className="flex items-start gap-3">
                  {getFailureIcon(failure.failure_type)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-bold uppercase ${getFailureTextColor(
                          failure.failure_type
                        )}`}
                      >
                        {failure.failure_type}
                      </span>
                      <span className="px-2 py-1 rounded text-xs font-mono bg-white border border-gray-300">
                        {failure.failure_code}
                      </span>
                    </div>

                    <p className={`text-sm font-medium ${getFailureTextColor(failure.failure_type)} mb-3`}>
                      {failure.message}
                    </p>

                    {/* Step Linkage */}
                    {stepInfo && (
                      <div className="flex items-center gap-2 text-xs text-gray-700 mb-3">
                        <Link2 className="w-4 h-4" />
                        <span>
                          Failed at step {stepInfo.seq}: <strong>{stepInfo.name}</strong>
                          <span className="text-gray-500 ml-2">({stepInfo.step_type})</span>
                        </span>
                      </div>
                    )}

                    {/* Recommendations */}
                    {recommendations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-300">
                        <h5 className="text-xs font-semibold text-gray-700 mb-2 uppercase">
                          Recommendations
                        </h5>
                        <ul className="space-y-1">
                          {recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                              <span className="text-gray-400 mt-0.5">•</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Failure Metadata */}
              <div className="bg-white bg-opacity-50 px-4 py-3 border-t border-gray-300">
                <div className="flex items-center justify-between text-xs text-gray-600">
                  <div>
                    <span className="font-medium">Failure ID:</span>{' '}
                    <code className="font-mono">{failure.failure_id.substring(0, 8)}...</code>
                  </div>
                  <div>
                    <span className="font-medium">Detected:</span>{' '}
                    {new Date(failure.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Failure Summary */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">
          Failure Distribution
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {(['tool', 'model', 'retrieval', 'orchestration'] as const).map(type => {
            const count = failures.filter(f => f.failure_type === type).length;

            if (count === 0) return null;

            return (
              <div key={type} className="text-center">
                <div className={`text-2xl font-bold ${getFailureTextColor(type)}`}>
                  {count}
                </div>
                <div className="text-xs text-gray-600 capitalize">{type}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default FailureBreakdown;
