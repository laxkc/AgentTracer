/**
 * TraceTimeline Component
 *
 * Displays a visual timeline of agent steps with:
 * - Ordered step sequence
 * - Step latency visualization
 * - Step metadata display
 * - Retry attempt highlighting
 *
 * This component is critical for execution debugging:
 * "Understand why the agent failed in under 60 seconds"
 */

import React, { useState } from 'react';
import { Clock, ChevronDown, ChevronRight } from 'lucide-react';

interface Step {
  step_id: string;
  seq: number;
  step_type: 'plan' | 'retrieve' | 'tool' | 'respond' | 'other';
  name: string;
  latency_ms: number;
  started_at: string;
  ended_at: string;
  metadata: Record<string, any>;
}

interface TraceTimelineProps {
  steps: Step[];
  runStarted: string;
  runEnded: string | null;
}

const TraceTimeline: React.FC<TraceTimelineProps> = ({ steps, runStarted, runEnded }) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  };

  const getStepColor = (stepType: string) => {
    switch (stepType) {
      case 'plan':
        return 'bg-purple-500';
      case 'retrieve':
        return 'bg-blue-500';
      case 'tool':
        return 'bg-green-500';
      case 'respond':
        return 'bg-orange-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStepTextColor = (stepType: string) => {
    switch (stepType) {
      case 'plan':
        return 'text-purple-700';
      case 'retrieve':
        return 'text-blue-700';
      case 'tool':
        return 'text-green-700';
      case 'respond':
        return 'text-orange-700';
      default:
        return 'text-gray-700';
    }
  };

  const formatLatency = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getTotalDuration = () => {
    if (!runEnded) return null;
    const start = new Date(runStarted);
    const end = new Date(runEnded);
    return end.getTime() - start.getTime();
  };

  const getStepPercentage = (latencyMs: number) => {
    const totalDuration = getTotalDuration();
    if (!totalDuration) return 0;
    return (latencyMs / totalDuration) * 100;
  };

  // Detect retry patterns (same step name, sequential)
  const getRetryInfo = (step: Step, index: number) => {
    if (step.metadata?.attempt) {
      return {
        isRetry: true,
        attempt: step.metadata.attempt,
      };
    }

    // Check if this is a retry by looking at previous steps
    const prevSteps = steps.slice(0, index);
    const sameNameCount = prevSteps.filter(s => s.name === step.name).length;

    if (sameNameCount > 0) {
      return {
        isRetry: true,
        attempt: sameNameCount + 1,
      };
    }

    return { isRetry: false, attempt: 1 };
  };

  if (steps.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No steps recorded for this run
      </div>
    );
  }

  const totalDuration = getTotalDuration();

  return (
    <div className="space-y-4">
      {/* Timeline Header */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Step Timeline</h3>
            <p className="text-sm text-gray-600 mt-1">
              {steps.length} steps • {totalDuration ? formatLatency(totalDuration) : 'Running...'}
            </p>
          </div>
          <div className="text-right text-sm text-gray-600">
            <div>Started: {formatTimestamp(runStarted)}</div>
            {runEnded && <div>Ended: {formatTimestamp(runEnded)}</div>}
          </div>
        </div>
      </div>

      {/* Timeline Steps */}
      <div className="relative">
        {/* Vertical timeline line */}
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-200"></div>

        {/* Steps */}
        <div className="space-y-4">
          {steps.map((step, index) => {
            const retryInfo = getRetryInfo(step, index);
            const isExpanded = expandedSteps.has(step.step_id);

            return (
              <div key={step.step_id} className="relative pl-20">
                {/* Step number badge */}
                <div
                  className={`absolute left-5 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${getStepColor(
                    step.step_type
                  )} z-10`}
                >
                  {step.seq}
                </div>

                {/* Step card */}
                <div
                  className={`bg-white rounded-lg border-2 ${
                    retryInfo.isRetry ? 'border-yellow-300' : 'border-gray-200'
                  } shadow-sm hover:shadow-md transition-shadow`}
                >
                  {/* Step header */}
                  <div
                    className="p-4 cursor-pointer"
                    onClick={() => toggleStep(step.step_id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${getStepTextColor(
                              step.step_type
                            )} bg-opacity-10`}
                            style={{
                              backgroundColor: getStepColor(step.step_type).replace('bg-', 'rgba(') + ', 0.1)',
                            }}
                          >
                            {step.step_type}
                          </span>
                          {retryInfo.isRetry && (
                            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 text-yellow-700">
                              Retry #{retryInfo.attempt}
                            </span>
                          )}
                        </div>
                        <h4 className="text-sm font-semibold text-gray-900">
                          {step.name}
                        </h4>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatLatency(step.latency_ms)}</span>
                          </div>
                          <span>{formatTimestamp(step.started_at)}</span>
                        </div>
                      </div>

                      {/* Latency bar */}
                      <div className="ml-4 flex items-center gap-2">
                        <div className="w-32 bg-gray-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full ${getStepColor(step.step_type)} transition-all`}
                            style={{
                              width: `${Math.min(100, getStepPercentage(step.latency_ms))}%`,
                            }}
                          ></div>
                        </div>
                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 p-4 bg-gray-50">
                      <h5 className="text-xs font-semibold text-gray-700 mb-2 uppercase">
                        Metadata
                      </h5>
                      {Object.keys(step.metadata).length === 0 ? (
                        <p className="text-sm text-gray-500 italic">No metadata</p>
                      ) : (
                        <div className="space-y-1">
                          {Object.entries(step.metadata).map(([key, value]) => (
                            <div
                              key={key}
                              className="flex items-start gap-2 text-sm"
                            >
                              <span className="font-medium text-gray-700 min-w-32">
                                {key}:
                              </span>
                              <span className="text-gray-600 font-mono">
                                {typeof value === 'object'
                                  ? JSON.stringify(value)
                                  : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="mt-3 pt-3 border-t border-gray-300">
                        <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                          <div>
                            <span className="font-medium">Step ID:</span>{' '}
                            <code className="font-mono">{step.step_id.substring(0, 8)}...</code>
                          </div>
                          <div>
                            <span className="font-medium">Duration:</span>{' '}
                            {formatLatency(step.latency_ms)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">
          Step Breakdown
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {['plan', 'retrieve', 'tool', 'respond'].map(type => {
            const typeSteps = steps.filter(s => s.step_type === type);
            const totalLatency = typeSteps.reduce((sum, s) => sum + s.latency_ms, 0);

            return (
              <div key={type} className="text-center">
                <div className={`text-2xl font-bold ${getStepTextColor(type)}`}>
                  {typeSteps.length}
                </div>
                <div className="text-xs text-gray-600 capitalize">{type}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatLatency(totalLatency)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TraceTimeline;
