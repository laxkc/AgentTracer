/**
 * Decisions Page
 *
 * Observed branch selections across runs.
 * Decisions are explicit choices recorded by agent code.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListChecks, Activity, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Select } from '../components/ui/select';
import { Input } from '../components/ui/input';
import { PageHeader } from '../components/PageHeader';
import { StatCardSkeleton, TableSkeleton } from '../components/ui/LoadingSkeleton';
import { ErrorEmptyState, NoSearchResultsEmptyState } from '../components/ui/EmptyState';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet } from '../lib/apiClient';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { safeDivide, safeToFixed } from '../utils/safemath';

interface Decision {
  decision_id: string;
  decision_type: string;
  selected: string;
  reason_code: string;
  confidence?: number;
  metadata: Record<string, any>;
  recorded_at: string;
  run_id: string;
  agent_id: string;
}

interface AgentRun {
  run_id: string;
  agent_id: string;
  decisions: Array<{
    decision_id: string;
    decision_type: string;
    selected: string;
    reason_code: string;
    confidence?: number;
    metadata: Record<string, any>;
    recorded_at: string;
  }>;
}

const Decisions: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const { handleError } = useErrorHandler();

  const [filters, setFilters] = useState({
    decisionType: '',
    agentId: '',
    minConfidence: 0,
  });

  useEffect(() => {
    fetchDecisions();
  }, []);

  const fetchDecisions = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiGet<AgentRun[]>(
        `${API_ENDPOINTS.RUNS}?page_size=100`,
        API_CONFIG.QUERY_API_BASE_URL
      );
      setRuns(response);
    } catch (err) {
      const appError = handleError(err, 'Decisions.fetchDecisions');
      setError(appError.message);
    } finally {
      setLoading(false);
    }
  };

  const allDecisions = useMemo(() => {
    const decisions: Decision[] = [];
    runs.forEach(run => {
      if (run.decisions && Array.isArray(run.decisions) && run.decisions.length > 0) {
        run.decisions.forEach(decision => {
          decisions.push({
            ...decision,
            run_id: run.run_id,
            agent_id: run.agent_id,
          });
        });
      }
    });
    return decisions;
  }, [runs]);

  const filteredDecisions = useMemo(() => {
    return allDecisions.filter(decision => {
      if (filters.decisionType && decision.decision_type !== filters.decisionType) {
        return false;
      }
      if (filters.agentId && !decision.agent_id.toLowerCase().includes(filters.agentId.toLowerCase())) {
        return false;
      }
      if (filters.minConfidence > 0 && (decision.confidence || 0) < filters.minConfidence) {
        return false;
      }
      return true;
    });
  }, [allDecisions, filters]);

  const decisionStats = useMemo(() => {
    const typeCount: Record<string, number> = {};
    allDecisions.forEach(decision => {
      typeCount[decision.decision_type] = (typeCount[decision.decision_type] || 0) + 1;
    });

    const mostCommonType = Object.entries(typeCount).sort((a, b) => b[1] - a[1])[0];
    const decisionsPerRun = safeDivide(allDecisions.length, runs.length || 1);

    return {
      total: allDecisions.length,
      mostCommonType: mostCommonType ? mostCommonType[0] : 'N/A',
      decisionsPerRun: safeToFixed(decisionsPerRun, 1, '0.0'),
    };
  }, [allDecisions, runs]);

  const uniqueDecisionTypes = useMemo(() => {
    return Array.from(new Set(allDecisions.map(d => d.decision_type)));
  }, [allDecisions]);

  const toggleRow = (key: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  const getDecisionTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      tool_selection: 'bg-blue-50 text-blue-700 border-blue-200',
      retrieval_strategy: 'bg-purple-50 text-purple-700 border-purple-200',
      response_mode: 'bg-green-50 text-green-700 border-green-200',
      retry_strategy: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      orchestration_path: 'bg-pink-50 text-pink-700 border-pink-200',
    };
    return colors[type] || 'bg-gray-50 text-gray-700 border-gray-200';
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-10 space-y-8">
        <div className="grid gap-6 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton rows={6} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-10">
        <ErrorEmptyState message={error} onRetry={fetchDecisions} />
      </div>
    );
  }

  const hasFilters =
    Boolean(filters.decisionType) || Boolean(filters.agentId) || filters.minConfidence > 0;

  const safeMetadata = (metadata: Record<string, any>) => {
    try {
      return JSON.stringify(metadata, null, 2);
    } catch (jsonError) {
      console.error('Failed to stringify decision metadata:', jsonError);
      return 'Unable to display metadata.';
    }
  };

  const getContextEntries = (metadata: Record<string, any>) => {
    const entries = Object.entries(metadata || {});
    const context = entries.filter(([key]) => key.toLowerCase() !== 'reasoning');
    const reasoning = entries.find(([key]) => key.toLowerCase() === 'reasoning');
    return { context, reasoning };
  };

  const formatContextLabel = (key: string) => {
    const normalized = key.replace(/_/g, ' ').trim();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  };

  return (
    <div className="container mx-auto px-4 py-10">
      <PageHeader
        title="Decisions"
        description="Observed branch selections across runs"
        onRefresh={fetchDecisions}
        loading={loading}
      />

      <section className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <div className="flex items-start gap-3">
          <div>
            <h2 className="text-sm font-semibold text-blue-900">What this page shows</h2>
            <p className="text-sm text-blue-800 mt-2">
              This page displays explicit branch selections recorded by agent code. It does not capture
              model reasoning or internal thoughts.
            </p>
            <div className="text-xs text-blue-700 mt-3 space-y-1">
              <p>Use this to track selection patterns and debug orchestration logic.</p>
              <p>Do not use this to judge intelligence or infer reasoning.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p
              className="text-sm text-gray-600"
              title="Number of declared branch selections across all runs. Not a measure of intelligence or complexity."
            >
              Branch Points
            </p>
            <ListChecks className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{decisionStats.total}</p>
          <p className="text-xs text-gray-500 mt-1">Explicit selections recorded</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p
              className="text-sm text-gray-600"
              title="Category with most branch points. Does not imply importance."
            >
              Most Frequent Category
            </p>
            <Activity className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-xl font-semibold text-gray-900">{decisionStats.mostCommonType}</p>
          <p className="text-xs text-gray-500 mt-1">Most common branch category</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p
              className="text-sm text-gray-600"
              title="Average number of branch points per run. Higher numbers don't mean better or worse agents."
            >
              Branch Density
            </p>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{decisionStats.decisionsPerRun}</p>
          <p className="text-xs text-gray-500 mt-1">Selections per run</p>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Select
            value={filters.decisionType}
            onChange={(e) => setFilters(prev => ({ ...prev, decisionType: e.target.value }))}
          >
            <option value="">All Branch Categories</option>
            {uniqueDecisionTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </Select>

          <Input
            type="text"
            placeholder="Agent ID"
            value={filters.agentId}
            onChange={(e) => setFilters(prev => ({ ...prev, agentId: e.target.value }))}
          />

          <Input
            type="number"
            placeholder="Min Declared Confidence (0-1)"
            min="0"
            max="1"
            step="0.1"
            value={filters.minConfidence}
            onChange={(e) => setFilters(prev => ({ ...prev, minConfidence: parseFloat(e.target.value) || 0 }))}
          />
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {filteredDecisions.length === 0 ? (
          hasFilters ? (
            <NoSearchResultsEmptyState onClear={() => {
              setFilters({ decisionType: '', agentId: '', minConfidence: 0 });
              setExpandedRows(new Set());
            }} />
          ) : (
            <div className="text-center py-12">
              <ListChecks className="w-10 h-10 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-900 font-medium">No Branch Selections Recorded</p>
              <p className="text-gray-500 text-sm mt-2">
                Decisions are only captured when agent code explicitly records them.
              </p>
              <div className="text-xs text-gray-500 mt-3 space-y-1">
                <p>1. Check that your agent uses run.record_decision()</p>
                <p>2. Verify the tracer is enabled</p>
                <p>3. Ensure runs completed successfully</p>
              </div>
            </div>
          )
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8">

                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  title="The category of branch point (e.g., routing, retrieval_strategy). Defined by agent code."
                >
                  Branch Category
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  title="The option selected at this branch point. Does not imply correctness or optimality."
                >
                  Chosen Path
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  title="Enum code recorded by developer. This is not model reasoning."
                >
                  Declared Reason
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  title="Developer-provided score (0.0–1.0). Not calibrated or comparable across agents."
                >
                  Declared Confidence
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Recorded At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredDecisions.map((decision) => {
                const rowKey = decision.decision_id;
                const isExpanded = expandedRows.has(rowKey);
                return (
                  <React.Fragment key={rowKey}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => toggleRow(rowKey)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded text-xs font-semibold border ${getDecisionTypeColor(decision.decision_type)}`}>
                          {decision.decision_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
                        {decision.selected}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {decision.reason_code}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {safeToFixed(decision.confidence, 2, 'N/A')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {decision.agent_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(decision.recorded_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Button
                          onClick={() => navigate(`/runs/${decision.run_id}`)}
                          variant="ghost"
                          size="sm"
                        >
                          View Run
                        </Button>
                      </td>
                    </tr>
                    {isExpanded && decision.metadata && (
                      <tr>
                        <td colSpan={8} className="px-6 py-4 bg-gray-50">
                          <div className="text-sm">
                            <p className="font-semibold text-gray-700">Branch Context</p>
                            <p className="text-xs text-gray-500 mt-1">
                              Conditions at time of selection. This is factual context, not explanatory reasoning.
                            </p>
                            <div className="mt-3 space-y-2 text-xs text-gray-700">
                              {(() => {
                                const metadataEntries = getContextEntries(decision.metadata);
                                if (metadataEntries.context.length === 0) {
                                  return (
                                    <div className="bg-white border border-gray-200 rounded p-3">
                                      {safeMetadata(decision.metadata)}
                                    </div>
                                  );
                                }
                                return (
                                  <ul className="space-y-1">
                                    {metadataEntries.context.map(([key, value]) => (
                                      <li key={key} className="flex items-start gap-2">
                                        <span className="text-gray-500">•</span>
                                        <span className="text-gray-600 font-medium">
                                          {formatContextLabel(key)}:
                                        </span>
                                        <span className="text-gray-700 break-all">
                                          {String(value)}
                                        </span>
                                      </li>
                                    ))}
                                  </ul>
                                );
                              })()}
                            </div>
                            {getContextEntries(decision.metadata).reasoning && (
                              <details className="mt-3">
                                <summary className="text-xs font-medium text-gray-600 cursor-pointer">
                                  Developer Note
                                </summary>
                                <p className="text-xs text-gray-500 mt-1">
                                  Optional note provided by developer, not an agent-generated explanation.
                                </p>
                                <div className="bg-white border border-gray-200 rounded p-3 text-xs mt-2">
                                  {String(getContextEntries(decision.metadata).reasoning?.[1])}
                                </div>
                              </details>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default Decisions;
