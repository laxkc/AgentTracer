-- ============================================================================
-- Decision Quality Tracking Migration
-- ============================================================================
--
-- Purpose: Add tables for decision and quality signal tracking
--
-- CRITICAL CONSTRAINTS:
-- - This is ADDITIVE ONLY - NO CORE TABLES MODIFIED
-- - All core tables (agent_runs, agent_steps, agent_failures) UNCHANGED
-- - Privacy-safe: Only structured enums and numeric values stored
-- - Rollback safe: Can be fully reverted without data loss
--
-- Tables Added:
-- - agent_decisions: Structured decision points
-- - agent_quality_signals: Observable quality indicators
--
-- Date: 2026-01-01
-- Version: 2.0.0
-- ============================================================================

BEGIN;

-- ============================================================================
-- Table: agent_decisions
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_decisions (
    -- Primary key
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys to core tables (CASCADE delete for cleanup)
    run_id UUID NOT NULL REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(step_id) ON DELETE CASCADE,

    -- Decision metadata (all enum-based)
    decision_type VARCHAR(100) NOT NULL CHECK (LENGTH(decision_type) > 0),
    selected VARCHAR(200) NOT NULL CHECK (LENGTH(selected) > 0),
    reason_code VARCHAR(100) NOT NULL CHECK (LENGTH(reason_code) > 0),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),

    -- Structured metadata only (JSONB for better query performance)
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for query optimization
CREATE INDEX idx_agent_decisions_run_id ON agent_decisions(run_id);
CREATE INDEX idx_agent_decisions_step_id ON agent_decisions(step_id);
CREATE INDEX idx_agent_decisions_decision_type ON agent_decisions(decision_type);
CREATE INDEX idx_agent_decisions_reason_code ON agent_decisions(reason_code);
CREATE INDEX idx_agent_decisions_type_reason ON agent_decisions(decision_type, reason_code);
CREATE INDEX idx_agent_decisions_recorded_at ON agent_decisions(recorded_at);

-- Comments for documentation
COMMENT ON TABLE agent_decisions IS 'Structured decision points made by agents during execution.';
COMMENT ON COLUMN agent_decisions.decision_type IS 'Type of decision (enum): tool_selection, retrieval_strategy, etc.';
COMMENT ON COLUMN agent_decisions.reason_code IS 'Structured reason code (enum, not free text)';
COMMENT ON COLUMN agent_decisions.confidence IS 'Decision confidence value (0.0-1.0)';
COMMENT ON COLUMN agent_decisions.metadata IS 'Privacy-safe structured metadata only';


-- ============================================================================
-- Table: agent_quality_signals
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_quality_signals (
    -- Primary key
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys to core tables (CASCADE delete for cleanup)
    run_id UUID NOT NULL REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(step_id) ON DELETE CASCADE,

    -- Signal metadata (all enum-based)
    signal_type VARCHAR(100) NOT NULL CHECK (LENGTH(signal_type) > 0),
    signal_code VARCHAR(100) NOT NULL CHECK (LENGTH(signal_code) > 0),
    value BOOLEAN NOT NULL,
    weight REAL CHECK (weight IS NULL OR (weight >= 0.0 AND weight <= 1.0)),

    -- Structured metadata only (JSONB for better query performance)
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for query optimization
CREATE INDEX idx_agent_quality_signals_run_id ON agent_quality_signals(run_id);
CREATE INDEX idx_agent_quality_signals_step_id ON agent_quality_signals(step_id);
CREATE INDEX idx_agent_quality_signals_signal_type ON agent_quality_signals(signal_type);
CREATE INDEX idx_agent_quality_signals_signal_code ON agent_quality_signals(signal_code);
CREATE INDEX idx_agent_quality_signals_type_code ON agent_quality_signals(signal_type, signal_code);
CREATE INDEX idx_agent_quality_signals_type_code_value ON agent_quality_signals(signal_type, signal_code, value);
CREATE INDEX idx_agent_quality_signals_recorded_at ON agent_quality_signals(recorded_at);

-- Comments for documentation
COMMENT ON TABLE agent_quality_signals IS 'Observable quality signals correlated with agent execution outcomes.';
COMMENT ON COLUMN agent_quality_signals.signal_type IS 'Type of signal (enum): schema_valid, empty_retrieval, etc.';
COMMENT ON COLUMN agent_quality_signals.signal_code IS 'Specific signal code (enum, not free text)';
COMMENT ON COLUMN agent_quality_signals.value IS 'Signal present (true) or absent (false)';
COMMENT ON COLUMN agent_quality_signals.weight IS 'Signal weight for correlation analysis (0.0-1.0)';
COMMENT ON COLUMN agent_quality_signals.metadata IS 'Privacy-safe structured metadata only';


-- ============================================================================
-- Privacy Validation Functions
-- ============================================================================

-- Function to validate decision metadata for privacy violations
CREATE OR REPLACE FUNCTION validate_decision_metadata()
RETURNS TRIGGER AS $$
DECLARE
    blocked_keys TEXT[] := ARRAY['prompt', 'response', 'reasoning', 'thought',
                                  'message', 'content', 'text', 'output', 'input',
                                  'chain_of_thought', 'explanation', 'rationale'];
    key TEXT;
BEGIN
    -- Check for blocked keys in metadata
    FOR key IN SELECT jsonb_object_keys(NEW.metadata)
    LOOP
        IF LOWER(key) = ANY(blocked_keys) THEN
            RAISE EXCEPTION 'Privacy violation: metadata key "%" is not allowed. Privacy constraint: no prompts, responses, or reasoning text.', key;
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to validate signal metadata for privacy violations
CREATE OR REPLACE FUNCTION validate_signal_metadata()
RETURNS TRIGGER AS $$
DECLARE
    blocked_keys TEXT[] := ARRAY['prompt', 'response', 'reasoning', 'thought',
                                  'message', 'content', 'text', 'output', 'input',
                                  'chain_of_thought', 'explanation', 'rationale'];
    key TEXT;
BEGIN
    -- Check for blocked keys in metadata
    FOR key IN SELECT jsonb_object_keys(NEW.metadata)
    LOOP
        IF LOWER(key) = ANY(blocked_keys) THEN
            RAISE EXCEPTION 'Privacy violation: metadata key "%" is not allowed. Privacy constraint: no prompts, responses, or reasoning text.', key;
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Triggers for Privacy Enforcement
-- ============================================================================

-- Trigger to enforce decision metadata privacy
CREATE TRIGGER enforce_decision_metadata_privacy
    BEFORE INSERT OR UPDATE ON agent_decisions
    FOR EACH ROW
    EXECUTE FUNCTION validate_decision_metadata();

-- Trigger to enforce signal metadata privacy
CREATE TRIGGER enforce_signal_metadata_privacy
    BEFORE INSERT OR UPDATE ON agent_quality_signals
    FOR EACH ROW
    EXECUTE FUNCTION validate_signal_metadata();


-- ============================================================================
-- Verification: Ensure Core Tables Unchanged
-- ============================================================================

-- This query verifies that core tables still exist with expected structure
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    -- Verify core tables exist
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('agent_runs', 'agent_steps', 'agent_failures');

    IF table_count != 3 THEN
        RAISE EXCEPTION 'Core tables missing or corrupted. Migration aborted.';
    END IF;

    -- Verify critical core columns exist
    SELECT COUNT(*) INTO table_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND (
        (table_name = 'agent_runs' AND column_name IN ('run_id', 'agent_id', 'agent_version', 'status'))
        OR (table_name = 'agent_steps' AND column_name IN ('step_id', 'run_id', 'seq', 'step_type'))
        OR (table_name = 'agent_failures' AND column_name IN ('failure_id', 'run_id', 'failure_type', 'failure_code'))
    );

    IF table_count < 12 THEN
        RAISE EXCEPTION 'Core columns missing or corrupted. Migration aborted.';
    END IF;

    RAISE NOTICE 'Core verification passed: All tables and columns intact.';
END $$;

COMMIT;

-- ============================================================================
-- Post-Migration Statistics
-- ============================================================================

-- Display table information
SELECT
    'Migration completed successfully' AS status,
    NOW() AS completed_at;

SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('agent_runs', 'agent_steps', 'agent_failures', 'agent_decisions', 'agent_quality_signals')
ORDER BY tablename;

-- ============================================================================
-- Rollback Script (For Reference)
-- ============================================================================
-- To rollback this migration, run:
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS enforce_decision_metadata_privacy ON agent_decisions;
-- DROP TRIGGER IF EXISTS enforce_signal_metadata_privacy ON agent_quality_signals;
-- DROP FUNCTION IF EXISTS validate_decision_metadata();
-- DROP FUNCTION IF EXISTS validate_signal_metadata();
-- DROP TABLE IF EXISTS agent_quality_signals;
-- DROP TABLE IF EXISTS agent_decisions;
-- COMMIT;
--
-- This will completely remove decision quality tracking tables without affecting core tables.
-- ============================================================================
