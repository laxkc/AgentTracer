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

  // Agent Runs
  RUNS: '/v1/runs',
  RUN_DETAIL: (runId: string) => `/v1/runs/${runId}`,
  RUN_STATS: '/v1/stats',

  // Behavioral Baselines
  BASELINES: '/v1/drift/baselines',
  BASELINE_DETAIL: (baselineId: string) => `/v1/drift/baselines/${baselineId}`,
  BASELINE_ACTIVATE: (baselineId: string) => `/v1/drift/baselines/${baselineId}/activate`,
  BASELINE_DEACTIVATE: (baselineId: string) => `/v1/drift/baselines/${baselineId}/deactivate`,

  // Behavioral Profiles
  PROFILES: '/v1/drift/profiles',
  PROFILE_DETAIL: (profileId: string) => `/v1/drift/profiles/${profileId}`,

  // Drift Detection
  DRIFT: '/v1/drift',
  DRIFT_DETAIL: (driftId: string) => `/v1/drift/${driftId}`,
  DRIFT_RESOLVE: (driftId: string) => `/v1/drift/${driftId}/resolve`,
  DRIFT_TIMELINE: '/v1/drift/timeline',
  DRIFT_SUMMARY: '/v1/drift/summary',
} as const;
