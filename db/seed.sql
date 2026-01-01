-- Agent Observability Platform - Seed Data
--
-- This file contains sample data for development and testing.
-- It demonstrates the Phase-1 data model with privacy-safe examples.

-- ============================================================================
-- Sample Agent Run 1: Successful customer support query
-- ============================================================================

INSERT INTO agent_runs (run_id, agent_id, agent_version, environment, status, started_at, ended_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440001',
    'customer_support_agent',
    '1.0.0',
    'production',
    'success',
    '2026-01-01 10:00:00+00',
    '2026-01-01 10:00:02.500+00'
);

-- Steps for Run 1
INSERT INTO agent_steps (step_id, run_id, seq, step_type, name, latency_ms, started_at, ended_at, metadata)
VALUES
    ('650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 0, 'plan', 'analyze_query', 50, '2026-01-01 10:00:00+00', '2026-01-01 10:00:00.050+00', '{"query_type": "billing", "priority": "high"}'),
    ('650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440001', 1, 'retrieve', 'search_knowledge_base', 100, '2026-01-01 10:00:00.050+00', '2026-01-01 10:00:00.150+00', '{"result_count": 3, "search_method": "semantic"}'),
    ('650e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440001', 2, 'tool', 'call_external_api', 200, '2026-01-01 10:00:00.150+00', '2026-01-01 10:00:00.350+00', '{"attempt": 1, "api": "customer_data_api", "http_status": 200}'),
    ('650e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440001', 3, 'respond', 'generate_response', 150, '2026-01-01 10:00:00.350+00', '2026-01-01 10:00:02.500+00', '{"response_length": 250, "sources_used": 3}');

-- ============================================================================
-- Sample Agent Run 2: Failed run with retry attempts
-- ============================================================================

INSERT INTO agent_runs (run_id, agent_id, agent_version, environment, status, started_at, ended_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440002',
    'customer_support_agent',
    '1.0.0',
    'production',
    'failure',
    '2026-01-01 10:05:00+00',
    '2026-01-01 10:05:03.800+00'
);

-- Steps for Run 2 (including retry attempts as separate spans)
INSERT INTO agent_steps (step_id, run_id, seq, step_type, name, latency_ms, started_at, ended_at, metadata)
VALUES
    ('650e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440002', 0, 'plan', 'analyze_query', 45, '2026-01-01 10:05:00+00', '2026-01-01 10:05:00.045+00', '{"query_type": "account", "priority": "medium"}'),
    ('650e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440002', 1, 'retrieve', 'search_knowledge_base', 95, '2026-01-01 10:05:00.045+00', '2026-01-01 10:05:00.140+00', '{"result_count": 5, "search_method": "semantic"}'),
    -- Retry attempt 1 (failed)
    ('650e8400-e29b-41d4-a716-446655440007', '550e8400-e29b-41d4-a716-446655440002', 2, 'tool', 'call_external_api', 1000, '2026-01-01 10:05:00.140+00', '2026-01-01 10:05:01.140+00', '{"attempt": 1, "api": "customer_data_api", "http_status": 500, "error_type": "Exception"}'),
    -- Retry attempt 2 (failed)
    ('650e8400-e29b-41d4-a716-446655440008', '550e8400-e29b-41d4-a716-446655440002', 3, 'tool', 'call_external_api', 1200, '2026-01-01 10:05:01.140+00', '2026-01-01 10:05:02.340+00', '{"attempt": 2, "api": "customer_data_api", "http_status": 500, "error_type": "Exception"}'),
    -- Retry attempt 3 (failed - final)
    ('650e8400-e29b-41d4-a716-446655440009', '550e8400-e29b-41d4-a716-446655440002', 4, 'tool', 'call_external_api', 1400, '2026-01-01 10:05:02.340+00', '2026-01-01 10:05:03.740+00', '{"attempt": 3, "api": "customer_data_api", "http_status": 500, "error_type": "Exception"}');

-- Failure record for Run 2
INSERT INTO agent_failures (run_id, step_id, failure_type, failure_code, message)
VALUES (
    '550e8400-e29b-41d4-a716-446655440002',
    '650e8400-e29b-41d4-a716-446655440009',
    'tool',
    'timeout',
    'External API failed after 3 attempts'
);

-- ============================================================================
-- Sample Agent Run 3: Different agent (staging environment)
-- ============================================================================

INSERT INTO agent_runs (run_id, agent_id, agent_version, environment, status, started_at, ended_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440003',
    'data_analysis_agent',
    '2.1.0',
    'staging',
    'success',
    '2026-01-01 11:00:00+00',
    '2026-01-01 11:00:05.200+00'
);

-- Steps for Run 3
INSERT INTO agent_steps (step_id, run_id, seq, step_type, name, latency_ms, started_at, ended_at, metadata)
VALUES
    ('650e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440003', 0, 'plan', 'analyze_data_request', 80, '2026-01-01 11:00:00+00', '2026-01-01 11:00:00.080+00', '{"data_type": "sales", "time_range": "last_30_days"}'),
    ('650e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440003', 1, 'retrieve', 'fetch_data', 2000, '2026-01-01 11:00:00.080+00', '2026-01-01 11:00:02.080+00', '{"record_count": 10000, "data_source": "postgresql"}'),
    ('650e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440003', 2, 'tool', 'run_analysis', 3000, '2026-01-01 11:00:02.080+00', '2026-01-01 11:00:05.080+00', '{"analysis_type": "aggregation", "computation_time_ms": 2950}'),
    ('650e8400-e29b-41d4-a716-446655440013', '550e8400-e29b-41d4-a716-446655440003', 3, 'respond', 'format_results', 120, '2026-01-01 11:00:05.080+00', '2026-01-01 11:00:05.200+00', '{"result_format": "json", "result_size_kb": 45}');

-- ============================================================================
-- Sample Agent Run 4: Model failure example
-- ============================================================================

INSERT INTO agent_runs (run_id, agent_id, agent_version, environment, status, started_at, ended_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440004',
    'customer_support_agent',
    '1.0.0',
    'production',
    'failure',
    '2026-01-01 12:00:00+00',
    '2026-01-01 12:00:01.500+00'
);

-- Steps for Run 4
INSERT INTO agent_steps (step_id, run_id, seq, step_type, name, latency_ms, started_at, ended_at, metadata)
VALUES
    ('650e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440004', 0, 'plan', 'analyze_query', 50, '2026-01-01 12:00:00+00', '2026-01-01 12:00:00.050+00', '{"query_type": "general", "priority": "low"}'),
    ('650e8400-e29b-41d4-a716-446655440015', '550e8400-e29b-41d4-a716-446655440004', 1, 'retrieve', 'search_knowledge_base', 100, '2026-01-01 12:00:00.050+00', '2026-01-01 12:00:00.150+00', '{"result_count": 0}'),
    ('650e8400-e29b-41d4-a716-446655440016', '550e8400-e29b-41d4-a716-446655440004', 2, 'respond', 'generate_response', 1350, '2026-01-01 12:00:00.150+00', '2026-01-01 12:00:01.500+00', '{"model": "gpt-4", "max_tokens": 500}');

-- Failure record for Run 4 (retrieval failure)
INSERT INTO agent_failures (run_id, step_id, failure_type, failure_code, message)
VALUES (
    '550e8400-e29b-41d4-a716-446655440004',
    '650e8400-e29b-41d4-a716-446655440015',
    'retrieval',
    'empty_retrieval',
    'No relevant knowledge base articles found for query'
);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Show summary of seeded data
SELECT
    'Runs' as type,
    COUNT(*) as count,
    STRING_AGG(DISTINCT agent_id, ', ') as agents,
    STRING_AGG(DISTINCT environment, ', ') as environments
FROM agent_runs

UNION ALL

SELECT
    'Steps' as type,
    COUNT(*) as count,
    STRING_AGG(DISTINCT step_type, ', ') as step_types,
    NULL as environments
FROM agent_steps

UNION ALL

SELECT
    'Failures' as type,
    COUNT(*) as count,
    STRING_AGG(DISTINCT failure_type, ', ') as failure_types,
    NULL as environments
FROM agent_failures;

-- Note: This seed data demonstrates Phase-1 privacy constraints:
-- ✅ No prompts or responses stored
-- ✅ Only safe metadata (codes, counts, types)
-- ✅ Retry modeling (each retry is a separate step)
-- ✅ Failure taxonomy (tool/model/retrieval/orchestration)
