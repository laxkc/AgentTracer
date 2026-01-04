/**
 * Phase 3 Specific Hooks
 * Custom hooks for drift, baselines, and profiles
 */

import { useApi, useApiMutation } from './useApi';
import { API_ENDPOINTS } from '../config/api';

// ============================================================================
// Type Definitions
// ============================================================================

export interface BehaviorDrift {
  drift_id: string;
  baseline_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  drift_type: 'decision' | 'signal' | 'latency';
  metric: string;
  baseline_value: number;
  observed_value: number;
  delta: number;
  delta_percent: number;
  significance: number;
  test_method: string;
  severity: 'low' | 'medium' | 'high';
  detected_at: string;
  observation_window_start: string;
  observation_window_end: string;
  observation_sample_size: number;
  resolved_at: string | null;
}

export interface BehaviorBaseline {
  baseline_id: string;
  profile_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_type: 'version' | 'time_window' | 'manual' | 'experiment';
  is_active: boolean;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  description: string | null;
}

export interface BehaviorProfile {
  profile_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  window_start: string;
  window_end: string;
  sample_size: number;
  decision_distributions: Record<string, Record<string, number>>;
  signal_distributions: Record<string, Record<string, number>>;
  latency_stats: {
    mean_run_duration_ms: number;
    p50_run_duration_ms: number;
    p95_run_duration_ms: number;
    p99_run_duration_ms: number;
  };
  created_at: string;
}

export interface DriftSummary {
  total_drift_events: number;
  unresolved_drift_events: number;
  drift_by_severity: Record<string, number>;
  drift_by_type: Record<string, number>;
  agents_with_drift: number;
}

// ============================================================================
// Drift Hooks
// ============================================================================

/**
 * Fetch all drift events
 */
export function useDrift(filters?: {
  agent_id?: string;
  agent_version?: string;
  environment?: string;
  severity?: string;
  resolved?: boolean;
  limit?: number;
}) {
  const queryParams = new URLSearchParams();

  if (filters?.agent_id) queryParams.append('agent_id', filters.agent_id);
  if (filters?.agent_version) queryParams.append('agent_version', filters.agent_version);
  if (filters?.environment) queryParams.append('environment', filters.environment);
  if (filters?.severity) queryParams.append('severity', filters.severity);
  if (filters?.resolved !== undefined) queryParams.append('resolved', String(filters.resolved));
  if (filters?.limit) queryParams.append('limit', String(filters.limit));

  const url = `${API_ENDPOINTS.DRIFT}?${queryParams.toString()}`;

  return useApi<BehaviorDrift[]>(url);
}

/**
 * Fetch single drift event by ID
 */
export function useDriftDetail(driftId: string | null) {
  const url = driftId ? API_ENDPOINTS.DRIFT_DETAIL(driftId) : '';

  return useApi<BehaviorDrift>(url, {
    enabled: !!driftId,
  });
}

/**
 * Fetch drift summary
 */
export function useDriftSummary(days: number = 7) {
  const url = `${API_ENDPOINTS.DRIFT_SUMMARY}?days=${days}`;

  return useApi<DriftSummary>(url);
}

/**
 * Resolve drift event
 */
export function useResolveDrift() {
  return useApiMutation<{ message: string }>('post', {
    showSuccessToast: true,
    successMessage: 'Drift event marked as resolved',
  });
}

// ============================================================================
// Baseline Hooks
// ============================================================================

/**
 * Fetch all baselines
 */
export function useBaselines(filters?: {
  agent_id?: string;
  agent_version?: string;
  environment?: string;
  is_active?: boolean;
  limit?: number;
}) {
  const queryParams = new URLSearchParams();

  if (filters?.agent_id) queryParams.append('agent_id', filters.agent_id);
  if (filters?.agent_version) queryParams.append('agent_version', filters.agent_version);
  if (filters?.environment) queryParams.append('environment', filters.environment);
  if (filters?.is_active !== undefined) queryParams.append('is_active', String(filters.is_active));
  if (filters?.limit) queryParams.append('limit', String(filters.limit));

  const url = `${API_ENDPOINTS.BASELINES}?${queryParams.toString()}`;

  return useApi<BehaviorBaseline[]>(url);
}

/**
 * Fetch single baseline by ID
 */
export function useBaselineDetail(baselineId: string | null) {
  const url = baselineId ? API_ENDPOINTS.BASELINE_DETAIL(baselineId) : '';

  return useApi<BehaviorBaseline>(url, {
    enabled: !!baselineId,
  });
}

/**
 * Create baseline
 */
export function useCreateBaseline() {
  return useApiMutation<BehaviorBaseline>('post', {
    showSuccessToast: true,
    successMessage: 'Baseline created successfully',
  });
}

/**
 * Activate baseline
 */
export function useActivateBaseline() {
  return useApiMutation<{ message: string }>('post', {
    showSuccessToast: true,
    successMessage: 'Baseline activated',
  });
}

/**
 * Deactivate baseline
 */
export function useDeactivateBaseline() {
  return useApiMutation<{ message: string }>('post', {
    showSuccessToast: true,
    successMessage: 'Baseline deactivated',
  });
}

// ============================================================================
// Profile Hooks
// ============================================================================

/**
 * Fetch all profiles
 */
export function useProfiles(filters?: {
  agent_id?: string;
  agent_version?: string;
  environment?: string;
  limit?: number;
}) {
  const queryParams = new URLSearchParams();

  if (filters?.agent_id) queryParams.append('agent_id', filters.agent_id);
  if (filters?.agent_version) queryParams.append('agent_version', filters.agent_version);
  if (filters?.environment) queryParams.append('environment', filters.environment);
  if (filters?.limit) queryParams.append('limit', String(filters.limit));

  const url = `${API_ENDPOINTS.PROFILES}?${queryParams.toString()}`;

  return useApi<BehaviorProfile[]>(url);
}

/**
 * Fetch single profile by ID
 */
export function useProfileDetail(profileId: string | null) {
  const url = profileId ? API_ENDPOINTS.PROFILE_DETAIL(profileId) : '';

  return useApi<BehaviorProfile>(url, {
    enabled: !!profileId,
  });
}
