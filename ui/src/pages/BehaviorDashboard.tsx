/**
 * Phase 3 - Behavior Dashboard (shadcn/ui Edition)
 *
 * Professional observability dashboard for agent behavioral stability
 */

import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  Filter,
  RefreshCw,
  X,
  Eye,
  GitCompare,
  Search,
  Users,
} from 'lucide-react';
import { useDrift, useDriftSummary, useBaselines } from '../hooks/usePhase3';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
  // State
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
  const [showOnlyDrift, setShowOnlyDrift] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Data fetching
  const { data: baselines, loading: loadingBaselines, error: baselinesError, refetch: refetchBaselines } = useBaselines({ limit: 1000 });
  const { data: driftEvents, loading: loadingDrift, error: driftError, refetch: refetchDrift } = useDrift({ resolved: false, limit: 1000 });
  const { data: summary, loading: loadingSummary, refetch: refetchSummary } = useDriftSummary(7);

  const loading = loadingBaselines || loadingDrift || loadingSummary;
  const error = baselinesError || driftError;

  // Process data
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

  // Filtering
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

  const environments = useMemo(() => Array.from(new Set(agentRows.map((r) => r.environment))), [agentRows]);
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

  const getSeverityVariant = (severity: string): "default" | "warning" | "destructive" => {
    if (severity === 'high') return 'destructive';
    if (severity === 'medium') return 'warning';
    return 'default';
  };

  const getEnvironmentVariant = (env: string): "default" | "success" | "warning" | "secondary" => {
    if (env === 'production') return 'success';
    if (env === 'staging') return 'warning';
    return 'secondary';
  };

  // Loading state
  if (loading) {
    return (
      <div className="container mx-auto p-6 space-y-6 max-w-7xl">
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

  // Error state
  if (error) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <ErrorEmptyState message={error} onRetry={refreshAll} />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-7xl">
      {/* Page Header - SINGLE INSTANCE */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Activity className="h-6 w-6 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">Behavior Dashboard</h1>
          </div>
          <p className="text-gray-500">
            Observational view of agent behavioral stability and detected changes
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refreshAll}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      {summary && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Agents Monitored</CardTitle>
              <Users className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(agentRows.length)}</div>
              <p className="text-xs text-gray-500">with active baselines</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Unresolved Drift</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">{formatNumber(summary.unresolved_drift_events)}</div>
              <p className="text-xs text-gray-500">changes detected</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Drift Events (7d)</CardTitle>
              <TrendingUp className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(summary.total_drift_events)}</div>
              <p className="text-xs text-gray-500">total detected</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Agents with Drift</CardTitle>
              <GitCompare className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(summary.agents_with_drift)}</div>
              <p className="text-xs text-gray-500">observing changes</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <CardTitle className="text-lg">Filters</CardTitle>
              {hasActiveFilters && <Badge variant="info">Active</Badge>}
            </div>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <label className="text-sm font-medium mb-2 block">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="Search agent ID or version..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Environment</label>
              <select
                value={environmentFilter}
                onChange={(e) => setEnvironmentFilter(e.target.value)}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <option value="all">All Environments</option>
                {environments.map((env) => (
                  <option key={env} value={env}>{capitalize(env)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Severity</label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <option value="all">All Severities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>

            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showOnlyDrift}
                  onChange={(e) => setShowOnlyDrift(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">Only with drift</span>
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agents Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Agent Behavior Summary
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({formatNumber(filteredRows.length)} {filteredRows.length === 1 ? 'agent' : 'agents'})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
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
                          <div className="font-medium text-orange-600">
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
                        <span className="text-gray-400">—</span>
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
                        <Link to={`/drift/timeline?agent_id=${row.agent_id}&agent_version=${row.agent_version}&environment=${row.environment}`}>
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
        </CardContent>
      </Card>

      {/* Info Note */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <p className="text-sm text-blue-900">
            <strong>Note:</strong> Drift detection is observational and descriptive. It identifies when behavioral
            patterns change but does not make judgments about quality or correctness. Human interpretation is required
            to determine if observed changes warrant investigation.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default BehaviorDashboard;
