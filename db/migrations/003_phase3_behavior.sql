-- Phase 3 Migration: Behavioral Drift Detection & Operational Guardrails
-- This migration creates tables for behavioral baselines, profiles, and drift detection
-- All tables are additive - no modifications to Phase 1 or Phase 2 tables

-- ============================================================================
-- Table: behavior_profiles
-- Purpose: Statistical snapshots of agent behavior over time windows
-- Data Source: Aggregated from Phase 2 (agent_decisions, agent_quality_signals)
-- ============================================================================

CREATE TABLE behavior_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Agent identification
    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,

    -- Time window for aggregation
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    sample_size INTEGER NOT NULL CHECK (sample_size >= 0),

    -- Statistical distributions (JSON)
    -- decision_distributions: {"tool_selection": {"api": 0.65, "cache": 0.30}}
    -- All probabilities normalized to sum to 1.0
    decision_distributions JSONB NOT NULL DEFAULT '{}',

    -- signal_distributions: {"schema_valid": {"full_match": 0.92, "partial_match": 0.06}}
    -- All probabilities normalized to sum to 1.0
    signal_distributions JSONB NOT NULL DEFAULT '{}',

    -- latency_stats: {"mean_run_duration_ms": 1234.5, "p50_run_duration_ms": 1100.0}
    latency_stats JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique profiles per time window
    CONSTRAINT unique_profile UNIQUE (agent_id, agent_version, environment, window_start, window_end)
);

-- Indexes for efficient querying
CREATE INDEX idx_behavior_profiles_agent ON behavior_profiles(agent_id, agent_version, environment);
CREATE INDEX idx_behavior_profiles_window ON behavior_profiles(window_start, window_end);
CREATE INDEX idx_behavior_profiles_created ON behavior_profiles(created_at DESC);

-- ============================================================================
-- Table: behavior_baselines
-- Purpose: Immutable approved baselines for drift comparison
-- Baselines reference profiles and are never modified after creation
-- ============================================================================

CREATE TABLE behavior_baselines (
    baseline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to behavior profile
    profile_id UUID NOT NULL REFERENCES behavior_profiles(profile_id) ON DELETE CASCADE,

    -- Agent identification (denormalized for query efficiency)
    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,

    -- Baseline type
    baseline_type VARCHAR(50) NOT NULL CHECK (baseline_type IN ('version', 'time_window', 'manual')),

    -- Human approval (optional)
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,

    -- Privacy-safe description (max 200 chars, validated by trigger)
    description VARCHAR(200),

    -- Active flag (only one active baseline per agent/version/env)
    is_active BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partial unique index: only one active baseline per (agent, version, env)
CREATE UNIQUE INDEX idx_behavior_baselines_unique_active
ON behavior_baselines(agent_id, agent_version, environment)
WHERE is_active = TRUE;

-- Indexes for efficient querying
CREATE INDEX idx_behavior_baselines_agent ON behavior_baselines(agent_id, agent_version, environment);
CREATE INDEX idx_behavior_baselines_active ON behavior_baselines(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_behavior_baselines_type ON behavior_baselines(baseline_type);
CREATE INDEX idx_behavior_baselines_created ON behavior_baselines(created_at DESC);

-- ============================================================================
-- Table: behavior_drift
-- Purpose: Records of detected behavioral changes
-- Drift is purely observational - does not imply good/bad
-- ============================================================================

CREATE TABLE behavior_drift (
    drift_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to baseline used for comparison
    baseline_id UUID NOT NULL REFERENCES behavior_baselines(baseline_id) ON DELETE CASCADE,

    -- Agent identification (denormalized for query efficiency)
    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,

    -- Drift classification
    drift_type VARCHAR(50) NOT NULL CHECK (drift_type IN ('decision', 'signal', 'latency')),

    -- Specific metric that drifted (e.g., "tool_selection.api", "schema_valid.full_match")
    metric VARCHAR(255) NOT NULL,

    -- Comparison values
    baseline_value FLOAT NOT NULL,
    observed_value FLOAT NOT NULL,
    delta FLOAT NOT NULL,
    delta_percent FLOAT NOT NULL,

    -- Statistical significance
    significance FLOAT NOT NULL,
    test_method VARCHAR(50) NOT NULL,

    -- Severity (based on magnitude, not quality judgment)
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),

    -- Detection metadata
    detected_at TIMESTAMP NOT NULL,

    -- Observation window
    observation_window_start TIMESTAMP NOT NULL,
    observation_window_end TIMESTAMP NOT NULL,
    observation_sample_size INTEGER NOT NULL,

    -- Resolution tracking (when drift resolved)
    resolved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX idx_behavior_drift_agent ON behavior_drift(agent_id, agent_version, environment);
CREATE INDEX idx_behavior_drift_detected ON behavior_drift(detected_at DESC);
CREATE INDEX idx_behavior_drift_resolved ON behavior_drift(resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_behavior_drift_type ON behavior_drift(drift_type);
CREATE INDEX idx_behavior_drift_severity ON behavior_drift(severity);
CREATE INDEX idx_behavior_drift_baseline ON behavior_drift(baseline_id);

-- ============================================================================
-- Table: alert_log
-- Purpose: Log of emitted alerts for detected drift
-- Optional table for tracking alert delivery
-- ============================================================================

CREATE TABLE alert_log (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to drift event
    drift_id UUID NOT NULL REFERENCES behavior_drift(drift_id) ON DELETE CASCADE,

    -- Alert content and delivery
    alert_message TEXT NOT NULL,
    alert_channel VARCHAR(50) NOT NULL, -- 'slack', 'pagerduty', 'email', 'webhook'

    -- Delivery tracking
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivery_status VARCHAR(50) DEFAULT 'sent' CHECK (delivery_status IN ('sent', 'failed', 'pending', 'retry'))
);

-- Indexes for efficient querying
CREATE INDEX idx_alert_log_drift ON alert_log(drift_id);
CREATE INDEX idx_alert_log_sent ON alert_log(sent_at DESC);
CREATE INDEX idx_alert_log_status ON alert_log(delivery_status);

-- ============================================================================
-- Privacy Enforcement Triggers
-- Ensure no sensitive data enters Phase 3 tables
-- ============================================================================

-- Trigger: Validate baseline description is privacy-safe
CREATE OR REPLACE FUNCTION validate_baseline_description()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.description IS NOT NULL THEN
        -- Check for blocked keywords (privacy-sensitive terms)
        IF NEW.description ~* '(prompt|response|reasoning|thought|message|content|text|output|input|chain_of_thought|explanation|rationale)' THEN
            RAISE EXCEPTION 'Baseline description contains forbidden keywords';
        END IF;

        -- Check length
        IF LENGTH(NEW.description) > 200 THEN
            RAISE EXCEPTION 'Baseline description too long (max 200 chars)';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_baseline_description
BEFORE INSERT OR UPDATE ON behavior_baselines
FOR EACH ROW
EXECUTE FUNCTION validate_baseline_description();

-- ============================================================================
-- Immutability Enforcement Triggers
-- Baselines are immutable once created (except activation status)
-- ============================================================================

-- Trigger: Prevent updates to baselines (except is_active)
CREATE OR REPLACE FUNCTION prevent_baseline_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow activation/deactivation only
    IF OLD.is_active != NEW.is_active THEN
        RETURN NEW;
    END IF;

    -- Allow approval updates if not yet approved
    IF OLD.approved_by IS NULL AND NEW.approved_by IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Prevent all other updates
    RAISE EXCEPTION 'Baselines are immutable after creation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_baseline_update
BEFORE UPDATE ON behavior_baselines
FOR EACH ROW
EXECUTE FUNCTION prevent_baseline_update();

-- ============================================================================
-- Data Validation Triggers
-- Ensure data integrity and correctness
-- ============================================================================

-- Trigger: Validate profile sample size is sufficient
CREATE OR REPLACE FUNCTION validate_profile_sample_size()
RETURNS TRIGGER AS $$
BEGIN
    -- Minimum sample size for valid profile (configurable threshold)
    IF NEW.sample_size < 30 THEN
        RAISE WARNING 'Profile sample size (%) is below recommended minimum (30)', NEW.sample_size;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_profile_sample_size
BEFORE INSERT ON behavior_profiles
FOR EACH ROW
EXECUTE FUNCTION validate_profile_sample_size();

-- ============================================================================
-- Comments for documentation
-- ============================================================================

COMMENT ON TABLE behavior_profiles IS 'Statistical snapshots of agent behavior aggregated from Phase 2 data';
COMMENT ON TABLE behavior_baselines IS 'Immutable approved baselines for drift comparison';
COMMENT ON TABLE behavior_drift IS 'Records of detected behavioral changes (observational only)';
COMMENT ON TABLE alert_log IS 'Log of emitted alerts for drift events';

COMMENT ON COLUMN behavior_profiles.decision_distributions IS 'Normalized probability distributions of decision types and selections';
COMMENT ON COLUMN behavior_profiles.signal_distributions IS 'Normalized probability distributions of quality signal types and codes';
COMMENT ON COLUMN behavior_profiles.latency_stats IS 'Statistical summary of latency (mean, p50, p95, p99)';

COMMENT ON COLUMN behavior_baselines.baseline_type IS 'Type of baseline: version (per version), time_window (time range), manual (human-approved)';
COMMENT ON COLUMN behavior_baselines.is_active IS 'Only one active baseline per (agent_id, agent_version, environment)';

COMMENT ON COLUMN behavior_drift.drift_type IS 'Category of drift: decision (decision distributions), signal (quality signals), latency (performance)';
COMMENT ON COLUMN behavior_drift.severity IS 'Magnitude-based severity (not quality judgment): low (<15%), medium (15-30%), high (>30%)';
COMMENT ON COLUMN behavior_drift.significance IS 'Statistical p-value from drift detection test';

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Verify tables created
DO $$
BEGIN
    RAISE NOTICE 'Phase 3 migration complete. Tables created:';
    RAISE NOTICE '  - behavior_profiles';
    RAISE NOTICE '  - behavior_baselines';
    RAISE NOTICE '  - behavior_drift';
    RAISE NOTICE '  - alert_log';
    RAISE NOTICE 'Triggers created:';
    RAISE NOTICE '  - validate_baseline_description';
    RAISE NOTICE '  - prevent_baseline_update';
    RAISE NOTICE '  - validate_profile_sample_size';
END $$;
