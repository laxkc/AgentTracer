-- AgentTracer Platform — Phase 1 Database Schema
--
-- Design Principles:
-- 1. Privacy-by-default: NO prompts, responses, or PII
-- 2. Decision-centric: Captures agent steps and failures
-- 3. Queryable: Indexed for fast retrieval by run_id, agent_id, time range
--
-- Created: 2026-01-01

-- ============================================================================
-- TABLE: agent_runs
-- Represents a single execution of an agent
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id UUID PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL DEFAULT 'production',
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failure', 'partial')),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Indexes for query performance
    CONSTRAINT valid_end_time CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- Indexes for efficient queries
CREATE INDEX idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_agent_version ON agent_runs(agent_version);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_started_at ON agent_runs(started_at DESC);
CREATE INDEX idx_agent_runs_environment ON agent_runs(environment);

-- ============================================================================
-- TABLE: agent_steps
-- Represents ordered steps within an agent run
-- Each retry is a separate step span (critical for Phase-1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_steps (
    step_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    step_type VARCHAR(50) NOT NULL CHECK (step_type IN ('plan', 'retrieve', 'tool', 'respond', 'other')),
    name VARCHAR(255) NOT NULL,
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL,

    -- Safe metadata only (no prompts, no responses, no PII)
    -- Examples: {"tool_name": "search_api", "http_status": 200, "retry_attempt": 1}
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_step_timing CHECK (ended_at >= started_at),
    CONSTRAINT unique_step_seq UNIQUE (run_id, seq)
);

-- Indexes for step queries
CREATE INDEX idx_agent_steps_run_id ON agent_steps(run_id);
CREATE INDEX idx_agent_steps_seq ON agent_steps(run_id, seq);
CREATE INDEX idx_agent_steps_type ON agent_steps(step_type);
CREATE INDEX idx_agent_steps_started_at ON agent_steps(started_at);

-- GIN index for JSONB metadata queries (if needed)
CREATE INDEX idx_agent_steps_metadata ON agent_steps USING GIN (metadata);

-- ============================================================================
-- TABLE: agent_failures
-- Semantic failure classification (Phase-1 taxonomy)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_failures (
    failure_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(step_id) ON DELETE SET NULL,

    -- Failure taxonomy (mandatory classification)
    failure_type VARCHAR(50) NOT NULL CHECK (failure_type IN ('tool', 'model', 'retrieval', 'orchestration')),
    failure_code VARCHAR(100) NOT NULL,

    -- Human-readable message (no PII, no prompt content)
    message TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- At least one failure per failed run
    CONSTRAINT valid_failure_code CHECK (LENGTH(failure_code) > 0)
);

-- Indexes for failure analysis
CREATE INDEX idx_agent_failures_run_id ON agent_failures(run_id);
CREATE INDEX idx_agent_failures_step_id ON agent_failures(step_id);
CREATE INDEX idx_agent_failures_type ON agent_failures(failure_type);
CREATE INDEX idx_agent_failures_code ON agent_failures(failure_code);

-- ============================================================================
-- COMMENTS (Documentation)
-- ============================================================================
COMMENT ON TABLE agent_runs IS 'Phase-1: Captures agent execution runs without prompts or responses';
COMMENT ON TABLE agent_steps IS 'Phase-1: Ordered steps with latency tracking. Each retry is a separate span.';
COMMENT ON TABLE agent_failures IS 'Phase-1: Semantic failure classification using mandatory taxonomy';

COMMENT ON COLUMN agent_steps.metadata IS 'Safe metadata only: tool names, HTTP codes, retry counts. NO prompts, responses, or PII.';
COMMENT ON COLUMN agent_failures.message IS 'Human-readable failure description. Must not contain PII or sensitive data.';
