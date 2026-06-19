# Test Reference

This document maps each test file and test function to the behaviors it validates.
It is intended as a debugging guide: if a test fails, use the referenced
behavior and code path to decide whether the test or the implementation is
incorrect.

Contents:
- Unit tests (SDK, core, models)
- Integration tests (API, DB, workflows)

## Unit Tests

### tests/unit/sdk/test_run_context.py

Covers `sdk/agenttrace.py`:
- `RunContext.__init__`, `RunContext.step`, `_add_step`
- `RunContext.record_failure`, `record_decision`, `record_quality_signal`
- `AgentTracer.start_run`, `RunContext.__enter__/__exit__`

Test cases:
- `test_create_run_context`: verifies `RunContext` stores agent metadata, assigns
  a UUID `run_id`, defaults status to `success`, and defers `started_at` until
  entering the context.
- `test_run_id_is_unique`: ensures separate `RunContext` instances do not share
  the same `run_id`.
- `test_run_context_manager_sets_timestamps`: ensures `RunContext.__enter__`
  sets `started_at` (and is a timezone-aware datetime).
- `test_record_single_step`: ensures `RunContext.step` creates a `StepContext`
  that records a single step entry with the correct type, name, and sequence.
- `test_step_sequence_numbering`: ensures step `seq` increments monotonically
  as steps are added.
- `test_valid_step_types`: ensures all allowed step types are accepted by the
  SDK (`plan`, `retrieve`, `tool`, `respond`, `other`).
- `test_record_failure`: ensures `record_failure` sets `_failure`, sets status
  to `failure`, and stores the failure taxonomy.
- `test_record_failure_with_step_id`: ensures failure can reference a step ID.
- `test_record_decision`: ensures decision entries are stored with required
  fields and candidates list.
- `test_record_quality_signal`: ensures quality signals are stored with the
  required fields and boolean `value`.

Debug hints:
- Failures here usually mean `RunContext` is not recording fields in `_steps`,
  `_failure`, `_decisions`, or `_quality_signals` as expected.
- Check `sdk/agenttrace.py` for field names, sequence handling, and defaults.

### tests/unit/sdk/test_step_context.py

Covers `sdk/agenttrace.py`:
- `StepContext.__enter__` and `__exit__` timing
- `StepContext.add_metadata` filtering rules
- `RunContext._add_step`

Test cases:
- `test_step_measures_duration`: verifies latency is at least the sleep time
  and stays within a reasonable bound.
- `test_step_timing_multiple_steps`: ensures each step captures its own latency.
- `test_zero_duration_step`: ensures near-zero steps still record non-negative
  latency.
- `test_step_with_metadata`: ensures metadata is stored on steps.
- `test_step_without_metadata`: ensures default metadata is an empty dict.
- `test_step_records_on_exception`: ensures step data is still recorded even if
  the block raises an exception.
- `test_step_timing_on_exception`: ensures timing still captured on exceptions.
- `test_valid_step_types_accepted`: ensures allowed step types are accepted.
- `test_empty_step_name_accepted`: confirms SDK does not reject empty names
  (validation happens at the API layer).

Debug hints:
- Timing tests depend on `StepContext.__exit__` creating a step entry with
  `latency_ms` computed from `started_at` and `ended_at`.
- Metadata tests depend on `StepContext.add_metadata` filtering behavior.

### tests/unit/sdk/test_tracer.py

Covers `sdk/agenttrace.py`:
- `AgentTracer.__init__`, `__enter__`, `__exit__`, `close`

Test cases:
- `test_create_tracer`: verifies default environment and API URL are set.
- `test_tracer_with_custom_environment`: verifies custom environment is stored.
- `test_tracer_with_custom_api_url`: verifies custom API URL is stored.
- `test_tracer_requires_agent_id`: requires `agent_id` at construction.
- `test_tracer_requires_agent_version`: requires `agent_version` at construction.
- `test_tracer_as_context_manager`: verifies context manager closes the HTTP
  client on exit.

Debug hints:
- Check defaults and `AgentTracer.close()` closing `self._client`.

### tests/unit/sdk/test_privacy_validation.py

Covers `sdk/agenttrace.py`:
- `StepContext.add_metadata` filters forbidden keys
- `RunContext` metadata acceptance and preservation

Test cases:
- `test_safe_metadata_in_run`: allows safe metadata in steps.
- `test_safe_metadata_in_step`: allows safe step metadata.
- `test_reject_prompt_in_metadata`: filters `prompt` key.
- `test_reject_response_in_metadata`: filters `response` key.
- `test_reject_reasoning_in_metadata`: documents current behavior for `reasoning`
  (SDK does not block it in `StepContext.add_metadata`).
- `test_reject_nested_unsafe_content`: confirms nested data is allowed since
  only top-level keys are checked.
- `test_forbidden_keyword_filtered`: filters each forbidden keyword in the
  SDK-level metadata filter.

Debug hints:
- The SDK-level filter is limited to top-level keys in `StepContext.add_metadata`.
- Strict privacy validation for decisions/signals is implemented separately in
  `_validate_decision_metadata`.

### tests/unit/models/test_pydantic_models.py

Covers `server/models/database.py` (Pydantic models):
- `AgentRunCreate`, `AgentStepCreate`, `AgentFailureCreate`
- `AgentDecisionCreate`, `AgentQualitySignalCreate`

Test cases:
- `test_valid_run_creation`: validates basic `AgentRunCreate` fields and status.
- `test_run_missing_required_fields`: missing required fields raises `ValidationError`.
- `test_run_invalid_status`: invalid `RunStatus` rejected.
- `test_run_with_nested_objects`: accepts runs with steps and failure.
- `test_valid_step_creation`: step accepts valid type and latency.
- `test_step_invalid_type`: rejects invalid `step_type`.
- `test_step_valid_types`: accepts all valid step types.
- `test_step_negative_latency`: rejects negative latency.
- `test_step_negative_sequence`: rejects negative seq.
- `test_valid_failure_creation`: validates basic failure taxonomy.
- `test_failure_missing_message`: missing message rejected.
- `test_failure_valid_types`: accepts all valid failure types.
- `test_valid_decision_creation`: validates decision fields and candidates.
- `test_decision_with_no_alternatives`: empty candidates allowed.
- `test_decision_selected_not_in_alternatives`: selected can be outside candidates.
- `test_valid_quality_signal_creation`: validates signal fields.
- `test_quality_signal_missing_fields`: missing required fields rejected.
- `test_quality_signal_with_metadata`: metadata preserved.
- `test_metadata_must_be_dict`: metadata must be a dict.
- `test_empty_metadata_allowed`: empty metadata allowed.
- `test_metadata_with_nested_objects`: nested metadata allowed in steps.

Debug hints:
- Validators live in `server/models/database.py` and enforce enum and privacy
  constraints for `AgentDecisionCreate` and `AgentQualitySignalCreate`.

### tests/unit/core/test_behavior_profiles.py

Covers `server/core/behavior_profiles.py`:
- `BehaviorProfileBuilder.build_profile`
- `_count_runs`, `_compute_decision_distributions`, `_compute_signal_distributions`
- `_compute_latency_stats`, `_calculate_percentiles`, `_normalize_distributions`

Test cases:
- `test_build_profile_success`: uses mocks to verify `build_profile` returns
  sample size and computed distribution/stats fields.
- `test_build_profile_insufficient_data`: ensures `InsufficientDataError` is
  raised when sample size < `min_sample_size`.
- `test_normalize_distributions`: verifies normalization to probabilities.
- `test_normalize_empty_distribution`: returns empty distributions when total is 0.
- `test_calculate_percentiles`: validates mean/p50/p95/p99 logic on sorted data.
- `test_calculate_percentiles_single_value`: handles single-item inputs.
- `test_percentile_monotonicity`: validates percentile ordering.
- `test_compute_decision_distributions`: ensures correct distribution
  computation from mocked query results.
- `test_compute_signal_distributions`: ensures correct signal distribution
  computation and normalization.

Debug hints:
- If percentiles are incorrect, check `_calculate_percentiles` index math.
- Distribution tests rely on `_normalize_distributions` to sum to ~1.0.

### tests/unit/core/test_baselines.py

Covers `server/core/baselines.py`:
- `BaselineManager.create_baseline`, `activate_baseline`, `deactivate_baseline`
- `approve_baseline`, `get_baseline`, `get_active_baseline`
- `_validate_description`

Test cases:
- `test_create_baseline_success`: ensures baseline persisted and committed.
- `test_create_baseline_invalid_type`: rejects invalid `baseline_type`.
- `test_create_baseline_valid_types`: accepts allowed types.
- `test_description_too_long`: rejects >200 chars.
- `test_description_forbidden_keywords`: rejects privacy-sensitive keywords.
- `test_description_safe_content`: accepts safe description.
- `test_activate_baseline`: sets active baseline and commits.
- `test_deactivate_baseline`: clears active flag.
- `test_activate_replaces_existing_active`: ensures previous baseline deactivated.
- `test_approve_baseline`: sets `approved_by` and `approved_at`.
- `test_approve_nonexistent_baseline`: raises `BaselineNotFoundError`.
- `test_get_baseline`: fetches baseline by ID.
- `test_get_active_baseline`: fetches active baseline for agent/version/env.

Debug hints:
- Validation uses `_validate_description` and `baseline_type` checks.
- Activation logic deactivates any existing active baseline for same agent tuple.

### tests/unit/core/test_drift_engine.py

Covers `server/core/drift_engine.py`:
- `DriftDetectionEngine.detect_drift`, `_run_chi_square_test`
- `_compare_decision_distributions`, `_compare_signal_distributions`
- `_compare_latency_stats`, `_calculate_severity`, `_is_significant`

Test cases:
- `test_no_drift_identical_distributions`: no drift when distributions match.
- `test_drift_detected_significant_shift`: drift records created on large shift.
- `test_drift_small_shift_not_detected`: small change does not trigger drift.
- `test_calculate_positive_delta`: validates delta math for increases.
- `test_calculate_negative_delta`: validates delta math for decreases.
- `test_delta_percent_with_zero_baseline`: zero baseline handled safely.
- `test_severity_thresholds`: local severity classification logic matches
  expected thresholds (note: uses simplified inline logic).
- `test_latency_drift_p95_increase`: large p95 increase implies drift.
- `test_latency_drift_within_tolerance`: small p95 change implies no drift.
- `test_p_value_range`: p-values in [0, 1].
- `test_significance_threshold`: compares p-values to threshold.
- `test_high_confidence_drift`: p < 0.01 indicates high confidence.
- `test_sufficient_sample_size`: sample size meets minimum.
- `test_insufficient_sample_size`: sample size below minimum.
- `test_minimum_sample_size_default`: default min sample size positive.
- `test_drift_event_has_required_fields`: drift record contains required fields.
- `test_drift_event_types`: drift type values are from allowed set.

Debug hints:
- Some tests are algorithmic sanity checks and do not call the engine directly.
- Drift thresholds are controlled by `_load_thresholds` default config.

## Integration Tests

### tests/integration/test_api_contracts.py

Covers `server/api/ingest.py` and `server/api/query.py` endpoint behavior.

Test cases (Ingest API):
- `test_ingest_run_success`: POST `/v1/runs` returns 201 and echoes `run_id`.
- `test_ingest_run_missing_required_field`: invalid payload returns 400/422.
- `test_ingest_run_invalid_status`: invalid status returns 400/422.
- `test_ingest_run_duplicate_id`: duplicate `run_id` is idempotent and returns
  the existing run data.
- `test_ingest_health_check`: GET `/health` returns healthy response.

Test cases (Query API):
- `test_list_runs_success`: GET `/v1/runs` returns 200 and a list.
- `test_list_runs_with_filters`: filtering and pagination parameters accepted.
- `test_get_run_by_id_success`: GET `/v1/runs/{id}` returns 200 after ingest.
- `test_get_run_not_found`: GET missing run returns 404 with error body.
- `test_get_steps_for_run`: GET `/v1/runs/{id}/steps` returns list.
- `test_get_failures_for_run`: GET `/v1/runs/{id}/failures` returns list.
- `test_query_health_check`: GET `/health` returns healthy response.

Test cases (Errors/headers/pagination):
- `test_400_error_format`: error response includes `detail` or `error`.
- `test_404_error_format`: error response includes `error` or `detail`.
- `test_500_error_handling`: placeholder for 500 responses (not implemented).
- `test_cors_headers_present`: OPTIONS provides CORS headers or valid status.
- `test_json_content_type`: responses include JSON content type.
- `test_pagination_limit`: page_size limits results.
- `test_pagination_offset`: page parameter produces different pages when data exists.

Debug hints:
- Idempotency is implemented in `_check_duplicate_run` in `server/api/ingest.py`.
- Query endpoints should return 404 for missing runs and missing steps.

### tests/integration/test_database_integrity.py

Covers ORM models and database constraints in `server/models/database.py`.

Test cases:
- `test_cascade_delete_run_deletes_steps`: deleting a run cascades steps.
- `test_cascade_delete_run_deletes_all_children`: cascades steps, failures,
  decisions, and signals.
- `test_duplicate_run_id_rejected`: unique constraint rejects duplicate `run_id`.
- `test_invalid_status_rejected`: enum check rejects invalid status.
- `test_invalid_step_type_rejected`: enum check rejects invalid step type.
- `test_rollback_on_error`: invalid insert triggers rollback.
- `test_ended_at_after_started_at`: end time must not precede start time.
- `test_agent_id_indexed`: index on `agent_id` supports efficient queries.

Debug hints:
- Check constraints and foreign keys are defined on the ORM models.
- Some behavior depends on database-level triggers/constraints.

### tests/integration/test_error_handling.py

Covers error handling and recovery across APIs and database.

Test cases:
- `test_partial_insert_rollback`: invalid child insert triggers rollback.
- `test_malformed_json`: malformed JSON returns 400/422.
- `test_empty_request_body`: empty request body returns 400/422.
- `test_wrong_content_type`: wrong content type yields 400/415/422.
- `test_duplicate_run_id_handled`: ingest handles duplicates idempotently.
- `test_invalid_foreign_key_handled`: invalid FK raises IntegrityError.
- `test_health_check_fails_when_db_down`: placeholder (not implemented).
- `test_503_when_db_unavailable`: placeholder (not implemented).
- `test_validation_error_details`: validation errors include field details.
- `test_multiple_validation_errors`: multiple invalid fields return 400/422.

Debug hints:
- Placeholder tests need infra control (stop/start DB) to implement.
- Error formats depend on FastAPI exception handlers in middleware.

### tests/integration/test_drift_workflow.py

Covers drift pipeline across `server/core/behavior_profiles.py`,
`server/core/baselines.py`, and `server/core/drift_engine.py`.

Test cases:
- `test_create_profile_with_sufficient_data`: 100 runs produce a behavior profile.
- `test_create_baseline_from_profile`: baseline created from profile.
- `test_activate_baseline`: baseline activation works.
- `test_detect_drift_with_distribution_shift`: drift detected on distribution shift.
- `test_resolve_drift_event`: placeholder for drift resolution.
- `test_full_drift_pipeline`: end-to-end pipeline with no drift detected.

Debug hints:
- Profile builder uses `min_sample_size` to gate profile creation.
- Drift detection relies on distribution shifts exceeding thresholds.

### tests/integration/test_e2e_telemetry.py

Covers end-to-end SDK to API to DB to query behavior.

Test cases:
- `test_ingest_complete_run`: SDK run with steps/decisions/signals is ingested
  and persisted in DB.
- `test_ingest_run_with_failure`: failure status recorded in DB.
- `test_query_run_by_id`: ingested run is queryable by ID.
- `test_list_runs`: list endpoint returns multiple runs.
- `test_query_steps_for_run`: steps endpoint returns step list.
- `test_full_round_trip`: SDK -> ingest -> query returns consistent run data.
- `test_timestamp_preservation`: `started_at` preserved within 1s tolerance.
- `test_metadata_preservation`: step metadata persists through pipeline.

Debug hints:
- Uses `AgentTracer` to generate runs; verify SDK payload shape if failures occur.
- Query endpoints return 404 on missing data; time.sleep helps eventual consistency.

## Known Gaps and Placeholders

These tests are placeholders and require infrastructure control or additional
setup to be meaningful:
- `tests/integration/test_api_contracts.py::test_500_error_handling`
- `tests/integration/test_error_handling.py::test_health_check_fails_when_db_down`
- `tests/integration/test_error_handling.py::test_503_when_db_unavailable`
- `tests/integration/test_drift_workflow.py::test_resolve_drift_event`

## Quick Debug Workflow

1. Identify the failing test in `tests/`.
2. Jump to the referenced code path in `sdk/agenttrace.py`,
   `server/models/database.py`, `server/core/*.py`, or `server/api/*.py`.
3. Compare the test's expected behavior (above) with current implementation.
4. If behavior is correct but test fails, adjust test data or environment.
5. If behavior is incorrect, fix implementation and re-run the test.
