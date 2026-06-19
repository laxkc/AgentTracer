/**
 * RunExplorer Component
 *
 * Browse and filter agent execution runs.
 *
 * Features:
 * - Filter by agent_id, status, environment, date range
 * - Pagination
 * - Click to view run details
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { Select } from './ui/select';
import { Input } from './ui/input';
import { DatePicker } from './ui/date-picker';
import { PageHeader } from './PageHeader';
import { TableSkeleton } from './ui/LoadingSkeleton';
import { ErrorEmptyState, NoDataEmptyState, NoSearchResultsEmptyState } from './ui/EmptyState';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from './ui/pagination';
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
}

interface Filters {
  agent_id: string;
  status: string;
  environment: string;
  start_time: string;
  end_time: string;
}

const RunExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const { handleError } = useErrorHandler();

  const [filters, setFilters] = useState<Filters>({
    agent_id: '',
    status: '',
    environment: '',
    start_time: '',
    end_time: '',
  });

  useEffect(() => {
    fetchRuns();
  }, [page, filters]);

  const fetchRuns = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (filters.agent_id) params.append('agent_id', filters.agent_id);
      if (filters.status) params.append('status', filters.status);
      if (filters.environment) params.append('environment', filters.environment);
      if (filters.start_time) params.append('start_time', filters.start_time);
      if (filters.end_time) params.append('end_time', filters.end_time);

      const response = await apiGet<AgentRun[]>(
        `${API_ENDPOINTS.RUNS}?${params.toString()}`,
        API_CONFIG.QUERY_API_BASE_URL
      );
      setRuns(response);
    } catch (err) {
      const appError = handleError(err, 'RunExplorer.fetchRuns');
      setError(appError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({
      agent_id: '',
      status: '',
      environment: '',
      start_time: '',
      end_time: '',
    });
    setPage(1);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failure':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'partial':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      default:
        return null;
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

  if (loading && runs.length === 0) {
    return (
      <div className="container mx-auto px-4 py-10 space-y-6">
        <TableSkeleton rows={8} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <ErrorEmptyState message={error} onRetry={fetchRuns} />
      </div>
    );
  }

  const hasFilters =
    Boolean(filters.agent_id) ||
    Boolean(filters.status) ||
    Boolean(filters.environment) ||
    Boolean(filters.start_time) ||
    Boolean(filters.end_time);

  return (
    <div className="container mx-auto px-4 py-10">
      <PageHeader
        title="Runs"
        description="Browse and filter agent execution history"
        onRefresh={fetchRuns}
        loading={loading}
        actions={
          <Button variant="outline" onClick={clearFilters}>
            Clear Filters
          </Button>
        }
      />

      <section className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Input
            type="text"
            placeholder="Agent ID"
            value={filters.agent_id}
            onChange={(e) => handleFilterChange('agent_id', e.target.value)}
          />
          <Select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
            <option value="partial">Partial</option>
          </Select>
          <Select
            value={filters.environment}
            onChange={(e) => handleFilterChange('environment', e.target.value)}
          >
            <option value="">All Environments</option>
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
          </Select>
          <DatePicker
            value={filters.start_time}
            onChange={(value) => handleFilterChange('start_time', value)}
            placeholder="Start date"
          />
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {runs.length === 0 ? (
          hasFilters ? (
            <NoSearchResultsEmptyState onClear={clearFilters} />
          ) : (
            <NoDataEmptyState entityName="runs" />
          )
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Started
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Steps
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {runs.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => navigate(`/runs/${run.run_id}`)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(run.status)}
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {run.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {run.agent_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatTimestamp(run.started_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDuration(run.started_at, run.ended_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {Array.isArray(run.steps) ? run.steps.length : 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="mt-6">
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              />
            </PaginationItem>
            <PaginationItem>
              <PaginationLink isActive>{page}</PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                onClick={() => setPage((p) => p + 1)}
                disabled={runs.length < pageSize}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      </div>
    </div>
  );
};

export default RunExplorer;
