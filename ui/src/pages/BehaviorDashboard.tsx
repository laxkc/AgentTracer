/**
 * Behavior Dashboard
 *
 * Observability dashboard for agent behavioral stability and drift detection
 */

import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, GitCompare } from 'lucide-react';
import { useDrift, useDriftSummary, useBaselines } from '../hooks/useBaselines';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { PageHeader } from '../components/PageHeader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  StatCardSkeleton,
  TableSkeleton,
} from '../components/ui/LoadingSkeleton';
import {
  NoDataEmptyState,
  NoSearchResultsEmptyState,
  ErrorEmptyState,
} from '../components/ui/EmptyState';
import { formatRelativeTime, formatNumber, capitalize } from '../utils/helpers';

interface AgentRow {
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_id: string | null;
  baseline_type: string | null;
  is_active: boolean;
  drift_count: number;
  unresolved_drift: number;
  latest_drift: {
    drift_id: string;
    severity: string;
    drift_type: string;
    detected_at: string;
  } | null;
}

const BehaviorDashboard: React.FC = () => {
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
  const [showOnlyDrift, setShowOnlyDrift] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const {
    data: baselines,
    loading: loadingBaselines,
    error: baselinesError,
    refetch: refetchBaselines,
  } = useBaselines({ limit: 1000 });
  const {
    data: driftEvents,
    loading: loadingDrift,
    error: driftError,
    refetch: refetchDrift,
  } = useDrift({ resolved: false, limit: 1000 });
  const { data: summary, loading: loadingSummary, refetch: refetchSummary } = useDriftSummary(7);

  const loading = loadingBaselines || loadingDrift || loadingSummary;
  const error = baselinesError || driftError;

  const agentRows: AgentRow[] = useMemo(() => {
    if (!baselines && !driftEvents) return [];
    const agentMap = new Map<string, AgentRow>();

    baselines?.forEach((baseline) => {
      const key = `${baseline.agent_id}|${baseline.agent_version}|${baseline.environment}`;
      if (!agentMap.has(key)) {
        agentMap.set(key, {
          agent_id: baseline.agent_id,
          agent_version: baseline.agent_version,
          environment: baseline.environment,
          baseline_id: baseline.baseline_id,
          baseline_type: baseline.baseline_type,
          is_active: baseline.is_active,
          drift_count: 0,
          unresolved_drift: 0,
          latest_drift: null,
        });
      }
    });

    driftEvents?.forEach((drift) => {
      const key = `${drift.agent_id}|${drift.agent_version}|${drift.environment}`;
      let row = agentMap.get(key);
      if (!row) {
        row = {
          agent_id: drift.agent_id,
          agent_version: drift.agent_version,
          environment: drift.environment,
          baseline_id: null,
          baseline_type: null,
          is_active: false,
          drift_count: 0,
          unresolved_drift: 0,
          latest_drift: null,
        };
        agentMap.set(key, row);
      }
      row.drift_count++;
      if (!drift.resolved_at) row.unresolved_drift++;
      if (!row.latest_drift || new Date(drift.detected_at) > new Date(row.latest_drift.detected_at)) {
        row.latest_drift = {
          drift_id: drift.drift_id,
          severity: drift.severity,
          drift_type: drift.drift_type,
          detected_at: drift.detected_at,
        };
      }
    });
    return Array.from(agentMap.values());
  }, [baselines, driftEvents]);

  const filteredRows = useMemo(() => {
    return agentRows.filter((row) => {
      if (environmentFilter !== 'all' && row.environment !== environmentFilter) return false;
      if (showOnlyDrift && row.unresolved_drift === 0) return false;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!row.agent_id.toLowerCase().includes(query) && !row.agent_version.toLowerCase().includes(query)) return false;
      }
      if (severityFilter !== 'all' && row.latest_drift?.severity !== severityFilter) return false;
      return true;
    });
  }, [agentRows, environmentFilter, showOnlyDrift, searchQuery, severityFilter]);

  const environments = useMemo(() => Array.from(new Set(agentRows.map((row) => row.environment))), [agentRows]);
  const hasActiveFilters = searchQuery || environmentFilter !== 'all' || severityFilter !== 'all' || showOnlyDrift;

  const clearFilters = () => {
    setSearchQuery('');
    setEnvironmentFilter('all');
    setSeverityFilter('all');
    setShowOnlyDrift(false);
  };

  const refreshAll = async () => {
    await Promise.all([refetchBaselines(), refetchDrift(), refetchSummary()]);
  };

  const getSeverityVariant = (severity: string): 'default' | 'warning' | 'destructive' => {
    if (severity === 'high') return 'destructive';
    if (severity === 'medium') return 'warning';
    return 'default';
  };

  const getEnvironmentVariant = (env: string): 'default' | 'success' | 'warning' | 'secondary' => {
    if (env === 'production') return 'success';
    if (env === 'staging') return 'warning';
    return 'secondary';
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-10 space-y-6">
        <div className="space-y-2">
          <div className="h-8 w-64 bg-gray-200 rounded animate-pulse" />
          <div className="h-4 w-96 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton rows={5} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-10">
        <ErrorEmptyState message={error} onRetry={refreshAll} />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-10 space-y-6">
      <PageHeader
        title="Behavior Dashboard"
        description="Observational view of agent behavioral stability and detected changes"
        onRefresh={refreshAll}
        loading={loading}
      />

      {summary && (
        <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <p className="text-sm text-gray-600">Agents Monitored</p>
            <p className="text-2xl font-semibold text-gray-900 mt-2">
              {formatNumber(agentRows.length)}
            </p>
            <p className="text-xs text-gray-500 mt-1">with active baselines</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <p className="text-sm text-gray-600">Unresolved Drift</p>
            <p className="text-2xl font-semibold text-gray-900 mt-2">
              {formatNumber(summary.unresolved_drift_events)}
            </p>
            <p className="text-xs text-gray-500 mt-1">changes detected</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <p className="text-sm text-gray-600">Drift Events (7d)</p>
            <p className="text-2xl font-semibold text-gray-900 mt-2">
              {formatNumber(summary.total_drift_events)}
            </p>
            <p className="text-xs text-gray-500 mt-1">total detected</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <p className="text-sm text-gray-600">Agents with Drift</p>
            <p className="text-2xl font-semibold text-gray-900 mt-2">
              {formatNumber(summary.agents_with_drift)}
            </p>
            <p className="text-xs text-gray-500 mt-1">observing changes</p>
          </div>
        </section>
      )}

      <section className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear
            </Button>
          )}
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <label className="text-sm font-medium mb-2 block">Search</label>
            <Input
              placeholder="Search agent ID or version..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Environment</label>
            <Select
              value={environmentFilter}
              onChange={(event) => setEnvironmentFilter(event.target.value)}
            >
              <option value="all">All Environments</option>
              {environments.map((env) => (
                <option key={env} value={env}>
                  {capitalize(env)}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Severity</label>
            <Select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </Select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showOnlyDrift}
                onChange={(event) => setShowOnlyDrift(event.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Only with drift
            </label>
          </div>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Agent behavior summary
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({formatNumber(filteredRows.length)} {filteredRows.length === 1 ? 'agent' : 'agents'})
            </span>
          </h2>
        </div>
        {filteredRows.length === 0 ? (
          <div className="p-8">
            {hasActiveFilters ? (
              <NoSearchResultsEmptyState onClear={clearFilters} />
            ) : (
              <NoDataEmptyState entityName="agents" />
            )}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Environment</TableHead>
                <TableHead>Baseline</TableHead>
                <TableHead>Drift Status</TableHead>
                <TableHead>Latest Event</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRows.map((row) => (
                <TableRow key={`${row.agent_id}-${row.agent_version}-${row.environment}`}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{row.agent_id}</div>
                      <div className="text-sm text-gray-500">v{row.agent_version}</div>
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge variant={getEnvironmentVariant(row.environment)}>
                      {capitalize(row.environment)}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    {row.baseline_id ? (
                      <div className="space-y-1">
                        <Badge variant={row.is_active ? 'success' : 'secondary'}>
                          {row.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        {row.baseline_type && (
                          <div className="text-xs text-gray-500">{capitalize(row.baseline_type)}</div>
                        )}
                      </div>
                    ) : (
                      <Badge variant="outline">No baseline</Badge>
                    )}
                  </TableCell>

                  <TableCell>
                    {row.unresolved_drift > 0 ? (
                      <div>
                        <div className="font-medium text-gray-900">
                          {formatNumber(row.unresolved_drift)} unresolved
                        </div>
                        {row.drift_count > 0 && (
                          <div className="text-xs text-gray-500">{formatNumber(row.drift_count)} total</div>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-500">No drift</span>
                    )}
                  </TableCell>

                  <TableCell>
                    {row.latest_drift ? (
                      <div className="space-y-1">
                        <div className="flex gap-1">
                          <Badge variant={getSeverityVariant(row.latest_drift.severity)}>
                            {capitalize(row.latest_drift.severity)}
                          </Badge>
                          <Badge variant="outline">{capitalize(row.latest_drift.drift_type)}</Badge>
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatRelativeTime(row.latest_drift.detected_at)}
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>

                  <TableCell>
                    <div className="flex gap-2">
                      {row.latest_drift && (
                        <Link to={`/drift/${row.latest_drift.drift_id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Button>
                        </Link>
                      )}
                      <Link
                        to={`/drift/timeline?agent_id=${row.agent_id}&agent_version=${row.agent_version}&environment=${row.environment}`}
                      >
                        <Button variant="ghost" size="sm">
                          <GitCompare className="h-4 w-4 mr-1" />
                          Timeline
                        </Button>
                      </Link>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      <section className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <p className="text-sm text-gray-700">
          <strong>Note:</strong> Drift detection is observational and descriptive. It identifies
          when behavioral patterns change but does not make judgments about quality or correctness.
        </p>
      </section>
    </div>
  );
};

export default BehaviorDashboard;
