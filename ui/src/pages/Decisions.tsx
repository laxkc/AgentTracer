/**
 * Decisions Page
 *
 * Track agent decision patterns and reasoning across runs.
 * Displays decision history with filtering and analytics.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListChecks, TrendingUp, Activity, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Select } from '../components/ui/select';
import { Input } from '../components/ui/input';
import { PageHeader } from '../components/PageHeader';
import { StatCardSkeleton, TableSkeleton } from '../components/ui/LoadingSkeleton';
import { ErrorEmptyState, NoDataEmptyState, NoSearchResultsEmptyState } from '../components/ui/EmptyState';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet } from '../lib/apiClient';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { safeAverage, safeDivide, safeToFixed } from '../utils/safemath';

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
    const avgConfidence = safeAverage(allDecisions.map((decision) => decision.confidence || 0));
    const decisionsPerRun = safeDivide(allDecisions.length, runs.length || 1);

    return {
      total: allDecisions.length,
      mostCommonType: mostCommonType ? mostCommonType[0] : 'N/A',
      avgConfidence: safeToFixed(avgConfidence, 2, '0.00'),
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

  return (
    <div className="container mx-auto px-4 py-10">
      <PageHeader
        title="Decisions"
        description="Track agent decision patterns and reasoning"
        onRefresh={fetchDecisions}
        loading={loading}
      />

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Total Decisions</p>
            <ListChecks className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{decisionStats.total}</p>
          <p className="text-xs text-gray-500 mt-1">Across all runs</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Most Common Type</p>
            <Activity className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-xl font-semibold text-gray-900">{decisionStats.mostCommonType}</p>
          <p className="text-xs text-gray-500 mt-1">Top decision type</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Avg Confidence</p>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{decisionStats.avgConfidence}</p>
          <p className="text-xs text-gray-500 mt-1">Average confidence score</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Decision Rate</p>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{decisionStats.decisionsPerRun}</p>
          <p className="text-xs text-gray-500 mt-1">Decisions per run</p>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Select
            value={filters.decisionType}
            onChange={(e) => setFilters(prev => ({ ...prev, decisionType: e.target.value }))}
          >
            <option value="">All Decision Types</option>
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
            placeholder="Min Confidence (0-1)"
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
            <NoDataEmptyState entityName="decisions" />
          )
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8">

                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Selected
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Reason
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Confidence
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
                            <p className="font-semibold text-gray-700 mb-2">Metadata:</p>
                            <pre className="bg-white border border-gray-200 rounded p-3 text-xs overflow-x-auto">
                              {safeMetadata(decision.metadata)}
                            </pre>
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
