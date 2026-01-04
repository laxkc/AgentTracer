/**
 * API Configuration
 * Centralized API endpoints and configuration
 */

// @ts-ignore - Vite env types
const VITE_QUERY_API_BASE_URL = import.meta.env?.VITE_QUERY_API_BASE_URL;
// @ts-ignore - Vite env types
const VITE_INGEST_API_BASE_URL = import.meta.env?.VITE_INGEST_API_BASE_URL;

export const API_CONFIG = {
  QUERY_API_BASE_URL: VITE_QUERY_API_BASE_URL || 'http://localhost:8001',
  INGEST_API_BASE_URL: VITE_INGEST_API_BASE_URL || 'http://localhost:8000',
  TIMEOUT: 10000, // 10 seconds
  RETRY_ATTEMPTS: 3,
} as const;

export const API_ENDPOINTS = {
  // Health
  HEALTH: '/health',

  // Phase 1 - Agent Runs
  RUNS: '/v1/runs',
  RUN_DETAIL: (runId: string) => `/v1/runs/${runId}`,
  RUN_STATS: '/v1/stats',

  // Phase 3 - Baselines
  BASELINES: '/v1/phase3/baselines',
  BASELINE_DETAIL: (baselineId: string) => `/v1/phase3/baselines/${baselineId}`,
  BASELINE_ACTIVATE: (baselineId: string) => `/v1/phase3/baselines/${baselineId}/activate`,
  BASELINE_DEACTIVATE: (baselineId: string) => `/v1/phase3/baselines/${baselineId}/deactivate`,

  // Phase 3 - Profiles
  PROFILES: '/v1/phase3/profiles',
  PROFILE_DETAIL: (profileId: string) => `/v1/phase3/profiles/${profileId}`,

  // Phase 3 - Drift
  DRIFT: '/v1/phase3/drift',
  DRIFT_DETAIL: (driftId: string) => `/v1/phase3/drift/${driftId}`,
  DRIFT_RESOLVE: (driftId: string) => `/v1/phase3/drift/${driftId}/resolve`,
  DRIFT_TIMELINE: '/v1/phase3/drift/timeline',
  DRIFT_SUMMARY: '/v1/phase3/drift/summary',
} as const;
