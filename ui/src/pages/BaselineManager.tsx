/**
 * Baseline Manager
 *
 * Manage behavioral baselines for drift detection
 */

import React, { useState } from 'react';
import {
  Database,
  Plus,
  RefreshCw,
  Filter,
  X,
  Eye,
  CheckCircle,
  XCircle,
  User,
} from 'lucide-react';
import { useBaselines, useProfileDetail, useCreateBaseline, useActivateBaseline, useDeactivateBaseline } from '../hooks/useBaselines';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import ViewBaselineDialog from '../components/ViewBaselineDialog';
import CreateBaselineDialog from '../components/CreateBaselineDialog';
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
import { formatDateTime, formatNumber, capitalize } from '../utils/helpers';
import { showToast } from '../utils/toast';

const BaselineManager: React.FC = () => {
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const [selectedBaselineId, setSelectedBaselineId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [baselineFormData, setBaselineFormData] = useState({
    agent_id: '',
    agent_version: '',
    environment: 'production',
    baseline_type: 'time_window',
    window_start: '',
    window_end: '',
    min_sample_size: 100,
    approved_by: '',
    description: '',
    auto_activate: false,
  });

  const { data: baselines, loading, error, refetch } = useBaselines({ limit: 1000 });
  const createMutation = useCreateBaseline();
  const activateMutation = useActivateBaseline();
  const deactivateMutation = useDeactivateBaseline();

  const selectedBaseline = baselines?.find(
    baseline => baseline.baseline_id === selectedBaselineId
  );
  const { data: selectedProfile } = useProfileDetail(selectedBaseline?.profile_id || null);

  const filteredBaselines = React.useMemo(() => {
    if (!baselines) return [];
    return baselines.filter(baseline => {
      if (environmentFilter !== 'all' && baseline.environment !== environmentFilter) return false;
      if (typeFilter !== 'all' && baseline.baseline_type !== typeFilter) return false;
      if (statusFilter === 'active' && !baseline.is_active) return false;
      if (statusFilter === 'inactive' && baseline.is_active) return false;
      return true;
    });
  }, [baselines, environmentFilter, typeFilter, statusFilter]);

  const stats = React.useMemo(() => {
    if (!baselines) return { total: 0, active: 0, agents: 0 };
    return {
      total: baselines.length,
      active: baselines.filter(baseline => baseline.is_active).length,
      agents: new Set(baselines.map(baseline => `${baseline.agent_id}-${baseline.agent_version}`)).size,
    };
  }, [baselines]);

  const environments = React.useMemo(() => {
    if (!baselines) return [];
    return Array.from(new Set(baselines.map(baseline => baseline.environment)));
  }, [baselines]);

  const types = React.useMemo(() => {
    if (!baselines) return [];
    return Array.from(new Set(baselines.map(baseline => baseline.baseline_type)));
  }, [baselines]);

  const hasActiveFilters = environmentFilter !== 'all' || typeFilter !== 'all' || statusFilter !== 'all';

  const clearFilters = () => {
    setEnvironmentFilter('all');
    setTypeFilter('all');
    setStatusFilter('all');
  };

  const handleCreateBaseline = async () => {
    if (!baselineFormData.agent_id || !baselineFormData.agent_version || !baselineFormData.window_start || !baselineFormData.window_end) {
      showToast.error('Please fill in all required fields');
      return;
    }

    const result = await createMutation.mutate('/v1/phase3/baselines', {
      ...baselineFormData,
      window_start: new Date(baselineFormData.window_start).toISOString(),
      window_end: new Date(baselineFormData.window_end).toISOString(),
    });

    if (result) {
      showToast.success('Baseline created successfully');
      setShowCreateModal(false);
      setBaselineFormData({
        agent_id: '',
        agent_version: '',
        environment: 'production',
        baseline_type: 'time_window',
        window_start: '',
        window_end: '',
        min_sample_size: 100,
        approved_by: '',
        description: '',
        auto_activate: false,
      });
      refetch();
    }
  };

  const handleActivate = async (baselineId: string) => {
    const result = await activateMutation.mutate(`/v1/phase3/baselines/${baselineId}/activate`);
    if (result) {
      showToast.success('Baseline activated');
      refetch();
    }
  };

  const handleDeactivate = async (baselineId: string) => {
    const result = await deactivateMutation.mutate(`/v1/phase3/baselines/${baselineId}/deactivate`);
    if (result) {
      showToast.success('Baseline deactivated');
      refetch();
    }
  };

  const getTypeVariant = (type: string): "default" | "secondary" | "outline" => {
    if (type === 'version') return 'default';
    if (type === 'time_window') return 'secondary';
    return 'outline';
  };

  const getEnvironmentVariant = (env: string): "default" | "success" | "warning" => {
    if (env === 'production') return 'success';
    if (env === 'staging') return 'warning';
    return 'default';
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6 space-y-6 max-w-7xl">
        <div className="space-y-2">
          <div className="h-8 w-64 bg-gray-200 rounded animate-pulse" />
          <div className="h-4 w-96 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton rows={5} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <ErrorEmptyState message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-7xl">
      {/* Page Header - SINGLE INSTANCE */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Database className="h-6 w-6 text-purple-600" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">Baseline Manager</h1>
          </div>
          <p className="text-gray-500">
            Manage behavioral baselines for drift detection
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refetch}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Baseline
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Baselines</CardTitle>
            <Database className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.total)}</div>
            <p className="text-xs text-gray-500">across all environments</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Baselines</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatNumber(stats.active)}</div>
            <p className="text-xs text-gray-500">currently monitoring</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Agents Covered</CardTitle>
            <User className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.agents)}</div>
            <p className="text-xs text-gray-500">agent versions</p>
          </CardContent>
        </Card>
      </div>

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
          <div className="grid gap-4 md:grid-cols-3">
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
              <label className="text-sm font-medium mb-2 block">Baseline Type</label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <option value="all">All Types</option>
                {types.map((type) => (
                  <option key={type} value={type}>{capitalize(type)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Baselines Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Baselines
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({formatNumber(filteredBaselines.length)} {filteredBaselines.length === 1 ? 'baseline' : 'baselines'})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {filteredBaselines.length === 0 ? (
            <div className="p-8">
              {hasActiveFilters ? (
                <NoSearchResultsEmptyState onClear={clearFilters} />
              ) : (
                <NoDataEmptyState
                  entityName="baselines"
                  onAction={() => setShowCreateModal(true)}
                  actionLabel="Create Baseline"
                />
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Environment</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBaselines.map((baseline) => (
                  <TableRow key={baseline.baseline_id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{baseline.agent_id}</div>
                        <div className="text-sm text-gray-500">v{baseline.agent_version}</div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <Badge variant={getEnvironmentVariant(baseline.environment)}>
                        {capitalize(baseline.environment)}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <Badge variant={getTypeVariant(baseline.baseline_type)}>
                        {capitalize(baseline.baseline_type)}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <Badge variant={baseline.is_active ? 'success' : 'secondary'}>
                        {baseline.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <div className="text-sm text-gray-500">
                        {formatDateTime(baseline.created_at)}
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedBaselineId(baseline.baseline_id)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View
                        </Button>
                        {baseline.is_active ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeactivate(baseline.baseline_id)}
                            disabled={deactivateMutation.loading}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Deactivate
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleActivate(baseline.baseline_id)}
                            disabled={activateMutation.loading}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Activate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* View Baseline Dialog */}
      <ViewBaselineDialog
        baseline={selectedBaseline || null}
        profile={selectedProfile || null}
        onClose={() => setSelectedBaselineId(null)}
      />

      {/* Create Baseline Dialog */}
      <CreateBaselineDialog
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        formData={baselineFormData}
        onFormChange={(field, value) => setBaselineFormData({ ...baselineFormData, [field]: value })}
        onSubmit={handleCreateBaseline}
        isLoading={createMutation.loading}
      />

      {/* Info Note */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <p className="text-sm text-blue-900">
            <strong>Note:</strong> Baselines are immutable once created. Only one baseline can be active per
            agent/version/environment combination. Activating a new baseline will automatically deactivate the
            previous one.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default BaselineManager;
