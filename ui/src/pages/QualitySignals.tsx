/**
 * Quality Signals Page
 *
 * Monitor quality indicators and their correlation with outcomes.
 * Displays signal monitoring with filtering and analytics.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, TrendingUp, TrendingDown, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Select } from '../components/ui/select';
import { Input } from '../components/ui/input';
import { PageHeader } from '../components/PageHeader';
import { StatCardSkeleton, TableSkeleton } from '../components/ui/LoadingSkeleton';
import { ErrorEmptyState, NoDataEmptyState, NoSearchResultsEmptyState } from '../components/ui/EmptyState';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet } from '../lib/apiClient';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { safeToFixed } from '../utils/safemath';

interface QualitySignal {
  signal_id: string;
  signal_type: string;
  signal_code: string;
  value: boolean;
  weight: number | null;
  metadata: Record<string, any>;
  recorded_at: string;
  run_id: string;
  agent_id: string;
}

interface AgentRun {
  run_id: string;
  agent_id: string;
  quality_signals: Array<{
    signal_id: string;
    signal_type: string;
    signal_code: string;
    value: boolean;
    weight: number | null;
    metadata: Record<string, any>;
    recorded_at: string;
  }>;
}

const QualitySignals: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>('');
  const { handleError } = useErrorHandler();

  const [filters, setFilters] = useState({
    signalType: '',
    signalCode: '',
    value: '',
    agentId: '',
  });

  useEffect(() => {
    fetchSignals();
  }, []);

  const fetchSignals = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiGet<AgentRun[]>(
        `${API_ENDPOINTS.RUNS}?page_size=100`,
        API_CONFIG.QUERY_API_BASE_URL
      );
      setRuns(response);
    } catch (err) {
      const appError = handleError(err, 'QualitySignals.fetchSignals');
      setError(appError.message);
    } finally {
      setLoading(false);
    }
  };

  const allSignals = useMemo(() => {
    const signals: QualitySignal[] = [];
    runs.forEach(run => {
      if (run.quality_signals && Array.isArray(run.quality_signals) && run.quality_signals.length > 0) {
        run.quality_signals.forEach(signal => {
          signals.push({
            ...signal,
            run_id: run.run_id,
            agent_id: run.agent_id,
          });
        });
      }
    });
    return signals;
  }, [runs]);

  const filteredSignals = useMemo(() => {
    let filtered = allSignals;

    if (selectedType) {
      filtered = filtered.filter(s => s.signal_type === selectedType);
    }

    if (filters.signalType && !selectedType) {
      filtered = filtered.filter(s => s.signal_type === filters.signalType);
    }

    if (filters.signalCode) {
      filtered = filtered.filter(s => s.signal_code.toLowerCase().includes(filters.signalCode.toLowerCase()));
    }

    if (filters.value) {
      const boolValue = filters.value === 'positive';
      filtered = filtered.filter(s => s.value === boolValue);
    }

    if (filters.agentId) {
      filtered = filtered.filter(s => s.agent_id.toLowerCase().includes(filters.agentId.toLowerCase()));
    }

    return filtered;
  }, [allSignals, filters, selectedType]);

  const signalStats = useMemo(() => {
    const positiveSignals = allSignals.filter(s => s.value === true).length;
    const negativeSignals = allSignals.filter(s => s.value === false).length;

    const typeCount: Record<string, number> = {};
    allSignals.forEach(signal => {
      typeCount[signal.signal_type] = (typeCount[signal.signal_type] || 0) + 1;
    });

    const mostCommonType = Object.entries(typeCount).sort((a, b) => b[1] - a[1])[0];

    return {
      total: allSignals.length,
      positive: positiveSignals,
      negative: negativeSignals,
      mostCommonType: mostCommonType ? mostCommonType[0] : 'N/A',
    };
  }, [allSignals]);

  const signalTypeGroups = useMemo(() => {
    const groups: Record<string, number> = {};
    allSignals.forEach(signal => {
      groups[signal.signal_type] = (groups[signal.signal_type] || 0) + 1;
    });
    return Object.entries(groups).sort((a, b) => b[1] - a[1]);
  }, [allSignals]);

  const uniqueSignalTypes = useMemo(() => {
    return Array.from(new Set(allSignals.map(s => s.signal_type)));
  }, [allSignals]);

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
        <ErrorEmptyState message={error} onRetry={fetchSignals} />
      </div>
    );
  }

  const hasFilters =
    Boolean(filters.signalType) ||
    Boolean(filters.signalCode) ||
    Boolean(filters.value) ||
    Boolean(filters.agentId) ||
    Boolean(selectedType);

  return (
    <div className="container mx-auto px-4 py-10">
      <PageHeader
        title="Quality Signals"
        description="Monitor quality indicators across agent runs"
        onRefresh={fetchSignals}
        loading={loading}
      />

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Total Signals</p>
            <Sparkles className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{signalStats.total}</p>
          <p className="text-xs text-gray-500 mt-1">Across all runs</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Positive Signals</p>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{signalStats.positive}</p>
          <p className="text-xs text-gray-500 mt-1">Value = true</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Negative Signals</p>
            <TrendingDown className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-3xl font-semibold text-gray-900">{signalStats.negative}</p>
          <p className="text-xs text-gray-500 mt-1">Value = false</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Most Common Type</p>
            <Sparkles className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-xl font-semibold text-gray-900">{signalStats.mostCommonType}</p>
          <p className="text-xs text-gray-500 mt-1">Top signal type</p>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Select
            value={filters.signalType}
            onChange={(e) => {
              setFilters(prev => ({ ...prev, signalType: e.target.value }));
              setSelectedType('');
            }}
          >
            <option value="">All Signal Types</option>
            {uniqueSignalTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </Select>

          <Input
            type="text"
            placeholder="Signal Code"
            value={filters.signalCode}
            onChange={(e) => setFilters(prev => ({ ...prev, signalCode: e.target.value }))}
          />

          <Select
            value={filters.value}
            onChange={(e) => setFilters(prev => ({ ...prev, value: e.target.value }))}
          >
            <option value="">All Values</option>
            <option value="positive">Positive (true)</option>
            <option value="negative">Negative (false)</option>
          </Select>

          <Input
            type="text"
            placeholder="Agent ID"
            value={filters.agentId}
            onChange={(e) => setFilters(prev => ({ ...prev, agentId: e.target.value }))}
          />
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Signal Types</h2>
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {signalTypeGroups.length > 0 ? (
              signalTypeGroups.map(([type, count]) => (
                <button
                  key={type}
                  onClick={() => setSelectedType(type === selectedType ? '' : type)}
                  className={`w-full text-left p-3 rounded-lg border transition ${
                    selectedType === type
                      ? 'bg-blue-50 border-blue-300'
                      : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{type}</span>
                    <span className="text-sm font-semibold text-blue-600">{count}</span>
                  </div>
                </button>
              ))
            ) : (
              <NoDataEmptyState entityName="signal types" />
            )}
          </div>
        </div>

        <div className="lg:col-span-3 bg-white border border-gray-200 rounded-lg overflow-hidden">
          {filteredSignals.length === 0 ? (
            hasFilters ? (
              <NoSearchResultsEmptyState onClear={() => {
                setFilters({ signalType: '', signalCode: '', value: '', agentId: '' });
                setSelectedType('');
              }} />
            ) : (
              <NoDataEmptyState entityName="signals" />
            )
          ) : (
            <div className="max-h-[500px] overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Code
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Value
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Weight
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
                  {filteredSignals.map((signal) => (
                    <tr key={signal.signal_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {signal.signal_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                        {signal.signal_code}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {signal.value ? (
                          <div className="flex items-center gap-1 text-green-600">
                            <CheckCircle className="w-4 h-4" />
                            <span className="text-sm font-medium">Positive</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-red-600">
                            <XCircle className="w-4 h-4" />
                            <span className="text-sm font-medium">Negative</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {safeToFixed(signal.weight, 2, 'N/A')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {signal.agent_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(signal.recorded_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Button
                          onClick={() => navigate(`/runs/${signal.run_id}`)}
                          variant="ghost"
                          size="sm"
                        >
                          View Run
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default QualitySignals;
