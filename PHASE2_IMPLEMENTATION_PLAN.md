# Phase 2 Implementation Plan
## AgentTracer Platform - Decision & Quality Signal Tracking

**Document Version:** 1.0
**Date:** 2026-01-01
**Status:** Planning Phase
**Target:** Phase 2 - Decision and Quality Observability

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 2 Objectives](#phase-2-objectives)
3. [Absolute Constraints](#absolute-constraints)
4. [Database Schema Design](#database-schema-design)
5. [SDK Extensions](#sdk-extensions)
6. [API Extensions](#api-extensions)
7. [UI Components](#ui-components)
8. [Privacy Enforcement](#privacy-enforcement)
9. [Testing Strategy](#testing-strategy)
10. [Implementation Phases](#implementation-phases)
11. [Backward Compatibility](#backward-compatibility)
12. [Rollout Strategy](#rollout-strategy)
13. [Success Criteria](#success-criteria)

---

## Executive Summary

Phase 2 extends the AgentTracer Platform from **execution observability** to **decision, quality, and outcome observability**.

### What Phase 2 Adds
- **AgentDecision**: Structured decision points with enum-based reason codes
- **AgentQualitySignal**: Atomic, factual quality indicators

### What Phase 2 Does NOT Do
- Store prompts, responses, or reasoning text
- Modify agent behavior
- Enforce correctness or policies
- Optimize or tune agents
- Introduce feedback loops

### Core Philosophy
> **Phase 2 explains behavior; it does not judge or change it.**

---

## Phase 2 Objectives

### Primary Goals

1. **Enable Decision Visibility**
   - Capture structured decision metadata
   - Track decision patterns across versions
   - Correlate decisions with outcomes

2. **Enable Quality Signal Tracking**
   - Record observable quality indicators
   - Track signal distributions over time
   - Compare signals across agent versions

3. **Enable Regression Analysis**
   - Identify decision pattern changes between versions
   - Correlate quality signal deltas with failures
   - Support root cause investigation

### Questions Phase 2 Answers

- "Why did the agent choose this path?"
- "Which decisions correlate with failures?"
- "What changed between version 1.0 and 1.1?"
- "Which quality signals indicate degraded outcomes?"
- "How do decision patterns differ across runs?"

### Questions Phase 2 Does NOT Answer

- "Is this the correct decision?" (No correctness judgment)
- "How should we fix this?" (No optimization)
- "What was the exact prompt?" (No prompt storage)

---

## Absolute Constraints

### Non-Negotiable Rules

These constraints must NEVER be violated:

#### Privacy Boundaries
- ❌ **NEVER** store raw prompts
- ❌ **NEVER** store LLM responses
- ❌ **NEVER** store chain-of-thought text
- ❌ **NEVER** store user messages
- ❌ **NEVER** store retrieved documents
- ❌ **NEVER** store tool payload contents
- ✅ **ONLY** store structured enums and identifiers

#### Behavioral Boundaries
- ❌ **NEVER** modify agent execution
- ❌ **NEVER** enforce policies
- ❌ **NEVER** block outputs
- ❌ **NEVER** auto-correct responses
- ❌ **NEVER** introduce feedback loops
- ✅ **ONLY** observe and record

#### Phase 1 Preservation
- ❌ **NEVER** modify AgentRun schema
- ❌ **NEVER** modify AgentStep schema
- ❌ **NEVER** modify AgentFailure schema
- ❌ **NEVER** alter Phase 1 ingest semantics
- ✅ **ONLY** add new tables and relationships

#### Semantic Boundaries
- ❌ **NEVER** claim correctness
- ❌ **NEVER** rank or score agents
- ❌ **NEVER** infer hidden reasoning
- ✅ **ONLY** present factual observations

---

## Database Schema Design

### Mental Model

```
AgentRun (Phase 1 - UNCHANGED)
├─ AgentDecision (Phase 2 - NEW, OPTIONAL)
├─ AgentQualitySignal (Phase 2 - NEW, OPTIONAL)
├─ AgentStep (Phase 1 - UNCHANGED)
└─ AgentFailure (Phase 1 - UNCHANGED)
```

### New Table: `agent_decisions`

**Purpose:** Store structured decision points made by agents

**Schema Design:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `decision_id` | UUID | NOT NULL | Primary key, unique decision identifier |
| `run_id` | UUID | NOT NULL | Foreign key to `agent_runs.run_id` |
| `step_id` | UUID | NULL | Foreign key to `agent_steps.step_id` (optional linkage) |
| `decision_type` | VARCHAR(100) | NOT NULL | Enum: tool_selection, retrieval_strategy, response_mode, etc. |
| `selected` | VARCHAR(200) | NOT NULL | The option that was selected |
| `reason_code` | VARCHAR(100) | NOT NULL | Enum-based reason (NOT free text) |
| `confidence` | FLOAT | NULL | Optional confidence value (0.0-1.0) |
| `recorded_at` | TIMESTAMP | NOT NULL | When decision was recorded |
| `metadata` | JSONB | NOT NULL | Structured metadata (enum/identifier only, validated) |

**Indexes:**
- Primary: `decision_id`
- Foreign keys: `run_id`, `step_id`
- Query optimization: `(run_id, decision_type)`, `(decision_type, reason_code)`

**Constraints:**
- `run_id` references `agent_runs.run_id` ON DELETE CASCADE
- `step_id` references `agent_steps.step_id` ON DELETE CASCADE
- `confidence` CHECK (confidence >= 0.0 AND confidence <= 1.0)
- `metadata` validated to prevent free-text fields

### New Table: `agent_quality_signals`

**Purpose:** Store atomic quality signals correlated with outcomes

**Schema Design:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `signal_id` | UUID | NOT NULL | Primary key, unique signal identifier |
| `run_id` | UUID | NOT NULL | Foreign key to `agent_runs.run_id` |
| `step_id` | UUID | NULL | Foreign key to `agent_steps.step_id` (optional linkage) |
| `signal_type` | VARCHAR(100) | NOT NULL | Enum: schema_valid, empty_retrieval, tool_success, etc. |
| `signal_code` | VARCHAR(100) | NOT NULL | Specific signal code within type |
| `value` | BOOLEAN | NOT NULL | Signal presence/absence |
| `weight` | FLOAT | NULL | Optional signal weight (for correlation analysis) |
| `recorded_at` | TIMESTAMP | NOT NULL | When signal was recorded |
| `metadata` | JSONB | NOT NULL | Structured metadata (enum/identifier only, validated) |

**Indexes:**
- Primary: `signal_id`
- Foreign keys: `run_id`, `step_id`
- Query optimization: `(run_id, signal_type)`, `(signal_type, signal_code, value)`

**Constraints:**
- `run_id` references `agent_runs.run_id` ON DELETE CASCADE
- `step_id` references `agent_steps.step_id` ON DELETE CASCADE
- `weight` CHECK (weight >= 0.0 AND weight <= 1.0)
- `metadata` validated to prevent free-text fields

### Enum Definitions

**Decision Types (Initial Set):**
```python
DECISION_TYPES = [
    "tool_selection",        # Choosing between available tools
    "retrieval_strategy",    # How to retrieve information
    "response_mode",         # How to format response
    "retry_strategy",        # Whether/how to retry
    "orchestration_path",    # Which execution path to take
]
```

**Reason Codes (Examples per Type):**
```python
REASON_CODES = {
    "tool_selection": [
        "fresh_data_required",
        "cached_data_sufficient",
        "tool_unavailable",
        "cost_optimization",
    ],
    "retrieval_strategy": [
        "semantic_search_preferred",
        "keyword_match_sufficient",
        "hybrid_approach_needed",
    ],
    "retry_strategy": [
        "transient_error_detected",
        "rate_limit_encountered",
        "no_retry_terminal_error",
    ],
}
```

**Signal Types (Initial Set):**
```python
SIGNAL_TYPES = [
    "schema_valid",           # Output matches expected schema
    "empty_retrieval",        # No documents retrieved
    "tool_success",           # Tool call succeeded
    "tool_failure",           # Tool call failed
    "retry_after_response",   # Retry occurred after response
    "latency_threshold",      # Operation exceeded latency threshold
    "token_usage_high",       # High token consumption
]
```

**Signal Codes (Examples per Type):**
```python
SIGNAL_CODES = {
    "schema_valid": [
        "full_match",
        "partial_match",
        "validation_failed",
    ],
    "empty_retrieval": [
        "no_results",
        "filtered_out",
    ],
    "tool_success": [
        "first_attempt",
        "after_retry",
    ],
}
```

### Migration Strategy

**Migration File:** `db/migrations/002_phase2_schema.sql`

**Contents:**
1. Create `agent_decisions` table
2. Create `agent_quality_signals` table
3. Create indexes
4. Add foreign key constraints
5. Create enum validation functions
6. Add trigger for `recorded_at` auto-population

**Rollback Strategy:**
- DROP tables in reverse order
- Verify Phase 1 tables unchanged
- Validate no orphaned data

**Data Retention:**
- Decisions and signals follow same retention as parent runs
- CASCADE deletes ensure consistency

---

## SDK Extensions

### Design Principles

1. **Optional by Default**: All Phase 2 APIs are opt-in
2. **Explicit Invocation**: No automatic decision/signal inference
3. **Fail-Safe**: Errors in Phase 2 APIs must not break agent execution
4. **Privacy-First**: Validate all metadata before transmission

### New SDK Methods

#### `run.record_decision()`

**Purpose:** Explicitly record a structured decision point

**Signature:**
```python
def record_decision(
    self,
    decision_type: str,          # Must be valid enum
    selected: str,               # The chosen option
    reason_code: str,            # Must be valid enum for type
    candidates: Optional[List[str]] = None,  # Other options considered
    confidence: Optional[float] = None,      # 0.0-1.0
    step_id: Optional[UUID] = None,          # Link to specific step
    metadata: Optional[Dict[str, Any]] = None  # Structured only
) -> None:
```

**Validation:**
- `decision_type` must be in allowed enum
- `reason_code` must be valid for the `decision_type`
- `confidence` must be between 0.0 and 1.0 if provided
- `metadata` validated for privacy violations (no free text)
- Errors logged but do not raise exceptions (fail-safe)

**Usage Example:**
```python
# User's agent code (explicit)
with tracer.start_run() as run:
    with run.step("plan", "choose_tool") as step:
        # Agent logic determines to use API over cache
        selected_tool = "call_api"

        # Explicitly record decision
        run.record_decision(
            decision_type="tool_selection",
            selected=selected_tool,
            reason_code="fresh_data_required",
            candidates=["call_api", "use_cache"],
            confidence=0.82,
            step_id=step.step_id
        )
```

**Implementation Notes:**
- Store decisions in memory buffer
- Transmit with run completion
- Include in `AgentRunCreate` payload (new optional field)
- Backend validates enums before storage

#### `run.record_quality_signal()`

**Purpose:** Explicitly record an observable quality indicator

**Signature:**
```python
def record_quality_signal(
    self,
    signal_type: str,            # Must be valid enum
    signal_code: str,            # Must be valid enum for type
    value: bool,                 # Signal present/absent
    weight: Optional[float] = None,  # 0.0-1.0
    step_id: Optional[UUID] = None,  # Link to specific step
    metadata: Optional[Dict[str, Any]] = None  # Structured only
) -> None:
```

**Validation:**
- `signal_type` must be in allowed enum
- `signal_code` must be valid for the `signal_type`
- `weight` must be between 0.0 and 1.0 if provided
- `metadata` validated for privacy violations
- Errors logged but do not raise exceptions (fail-safe)

**Usage Example:**
```python
# User's agent code (explicit)
with tracer.start_run() as run:
    with run.step("retrieve", "search_docs") as step:
        results = vector_search(query)

        # Explicitly record quality signal
        run.record_quality_signal(
            signal_type="empty_retrieval" if len(results) == 0 else "retrieval_success",
            signal_code="no_results" if len(results) == 0 else "results_found",
            value=True,
            step_id=step.step_id,
            metadata={"result_count": len(results)}  # Numeric metadata OK
        )
```

**Implementation Notes:**
- Store signals in memory buffer
- Transmit with run completion
- Include in `AgentRunCreate` payload (new optional field)
- Backend validates enums before storage

### Privacy Validation

**SDK-Level Validation:**
- Check metadata keys against blocklist: `["prompt", "response", "reasoning", "thought", "message", "content", "text", "output", "input"]`
- Validate metadata values are not long strings (max 100 chars)
- Ensure metadata values are primitives (str, int, float, bool)
- Reject deeply nested metadata structures

**Validation Function:**
```python
def _validate_phase2_metadata(metadata: Dict[str, Any]) -> None:
    """
    Validate Phase 2 metadata for privacy violations.
    Raises ValueError if unsafe data detected.
    """
    BLOCKED_KEYS = {"prompt", "response", "reasoning", "thought",
                    "message", "content", "text", "output", "input",
                    "chain_of_thought", "explanation", "rationale"}

    for key, value in metadata.items():
        # Check blocked keys
        if key.lower() in BLOCKED_KEYS:
            raise ValueError(f"Metadata key '{key}' may contain sensitive data")

        # Check value types
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise ValueError(f"Metadata value for '{key}' must be primitive type")

        # Check string lengths
        if isinstance(value, str) and len(value) > 100:
            raise ValueError(f"Metadata string '{key}' exceeds 100 characters")
```

### Backward Compatibility

**Guarantees:**
- If Phase 2 methods are not called, behavior is identical to Phase 1
- Phase 2 payload fields are optional in ingest API
- Phase 1 clients continue to work without modification
- Feature flag allows disabling Phase 2 entirely

---

## API Extensions

### Ingest API Changes

#### New Optional Fields in `AgentRunCreate`

**Pydantic Model Extension:**
```python
class AgentRunCreate(BaseModel):
    # Phase 1 fields (UNCHANGED)
    run_id: UUID
    agent_id: str
    agent_version: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    latency_ms: Optional[int]
    steps: List[AgentStepCreate]
    failure: Optional[AgentFailureCreate]

    # Phase 2 fields (NEW, OPTIONAL)
    decisions: Optional[List[AgentDecisionCreate]] = Field(default_factory=list)
    quality_signals: Optional[List[AgentQualitySignalCreate]] = Field(default_factory=list)
```

**New Models:**
```python
class AgentDecisionCreate(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    step_id: Optional[UUID] = None
    decision_type: str
    selected: str
    reason_code: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('decision_type')
    def validate_decision_type(cls, v):
        if v not in DECISION_TYPES:
            raise ValueError(f"Invalid decision_type: {v}")
        return v

    @validator('reason_code')
    def validate_reason_code(cls, v, values):
        decision_type = values.get('decision_type')
        if decision_type and v not in REASON_CODES.get(decision_type, []):
            raise ValueError(f"Invalid reason_code '{v}' for decision_type '{decision_type}'")
        return v

    @validator('metadata')
    def validate_metadata_privacy(cls, v):
        _validate_phase2_metadata(v)
        return v

class AgentQualitySignalCreate(BaseModel):
    signal_id: UUID = Field(default_factory=uuid4)
    step_id: Optional[UUID] = None
    signal_type: str
    signal_code: str
    value: bool
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('signal_type')
    def validate_signal_type(cls, v):
        if v not in SIGNAL_TYPES:
            raise ValueError(f"Invalid signal_type: {v}")
        return v

    @validator('signal_code')
    def validate_signal_code(cls, v, values):
        signal_type = values.get('signal_type')
        if signal_type and v not in SIGNAL_CODES.get(signal_type, []):
            raise ValueError(f"Invalid signal_code '{v}' for signal_type '{signal_type}'")
        return v

    @validator('metadata')
    def validate_metadata_privacy(cls, v):
        _validate_phase2_metadata(v)
        return v
```

**Ingest Endpoint Behavior:**
- Accept Phase 2 fields if present
- Validate enums strictly
- Reject if privacy validation fails
- Continue Phase 1 ingestion even if Phase 2 fails (log error)
- Feature flag to disable Phase 2 ingestion entirely

### Query API Extensions

#### New Endpoints

**1. Decision Aggregation: `GET /v1/decisions/aggregate`**

**Purpose:** Aggregate decisions by type, reason code, agent version

**Query Parameters:**
- `agent_id` (optional): Filter by agent
- `agent_version` (optional): Filter by version
- `decision_type` (optional): Filter by decision type
- `start_time` (optional): Time range start
- `end_time` (optional): Time range end

**Response:**
```json
{
  "aggregations": [
    {
      "decision_type": "tool_selection",
      "reason_code": "fresh_data_required",
      "count": 42,
      "avg_confidence": 0.78,
      "agent_versions": ["1.0.0", "1.1.0"]
    }
  ],
  "total_decisions": 150
}
```

**2. Quality Signal Aggregation: `GET /v1/signals/aggregate`**

**Purpose:** Aggregate quality signals by type, code, value

**Query Parameters:**
- `agent_id` (optional): Filter by agent
- `agent_version` (optional): Filter by version
- `signal_type` (optional): Filter by signal type
- `start_time` (optional): Time range start
- `end_time` (optional): Time range end

**Response:**
```json
{
  "aggregations": [
    {
      "signal_type": "schema_valid",
      "signal_code": "full_match",
      "true_count": 85,
      "false_count": 15,
      "true_percentage": 85.0
    }
  ],
  "total_signals": 100
}
```

**3. Version Comparison: `GET /v1/compare/versions`**

**Purpose:** Compare decision/signal distributions across agent versions

**Query Parameters:**
- `agent_id` (required): Agent to compare
- `version_a` (required): First version
- `version_b` (required): Second version
- `start_time` (optional): Time range start
- `end_time` (optional): Time range end

**Response:**
```json
{
  "comparison": {
    "version_a": "1.0.0",
    "version_b": "1.1.0",
    "decision_deltas": [
      {
        "decision_type": "tool_selection",
        "reason_code": "fresh_data_required",
        "version_a_count": 50,
        "version_b_count": 75,
        "delta_percentage": 50.0
      }
    ],
    "signal_deltas": [
      {
        "signal_type": "schema_valid",
        "signal_code": "full_match",
        "version_a_true_rate": 0.85,
        "version_b_true_rate": 0.92,
        "delta": 0.07
      }
    ]
  }
}
```

**4. Decision-Failure Correlation: `GET /v1/correlate/decisions-failures`**

**Purpose:** Identify which decisions correlate with failures

**Query Parameters:**
- `agent_id` (optional): Filter by agent
- `agent_version` (optional): Filter by version
- `failure_type` (optional): Filter by failure type

**Response:**
```json
{
  "correlations": [
    {
      "decision_type": "retry_strategy",
      "reason_code": "no_retry_terminal_error",
      "total_occurrences": 20,
      "runs_with_failures": 18,
      "correlation_rate": 0.90,
      "associated_failure_types": {
        "tool": 15,
        "model": 3
      }
    }
  ]
}
```

**5. Signal-Outcome Correlation: `GET /v1/correlate/signals-outcomes`**

**Purpose:** Identify which signals correlate with success/failure

**Query Parameters:**
- `agent_id` (optional): Filter by agent
- `agent_version` (optional): Filter by version
- `outcome` (optional): success, failure, partial

**Response:**
```json
{
  "correlations": [
    {
      "signal_type": "empty_retrieval",
      "signal_code": "no_results",
      "total_occurrences": 30,
      "success_rate_when_present": 0.20,
      "success_rate_when_absent": 0.85,
      "correlation_strength": -0.65
    }
  ]
}
```

**6. Run Details with Phase 2: `GET /v1/runs/{run_id}/details`**

**Purpose:** Extended run details including decisions and signals

**Response Extension:**
```json
{
  "run": { /* Phase 1 data */ },
  "steps": [ /* Phase 1 data */ ],
  "failure": { /* Phase 1 data */ },
  "decisions": [
    {
      "decision_id": "uuid",
      "step_id": "uuid",
      "decision_type": "tool_selection",
      "selected": "call_api",
      "reason_code": "fresh_data_required",
      "confidence": 0.82
    }
  ],
  "quality_signals": [
    {
      "signal_id": "uuid",
      "step_id": "uuid",
      "signal_type": "schema_valid",
      "signal_code": "full_match",
      "value": true
    }
  ]
}
```

### API Implementation Notes

**Privacy Preservation:**
- All responses contain only structured enums and numeric aggregations
- No free-text fields exposed
- No metadata returned in aggregations (only in detail views)

**Performance Considerations:**
- Add database indexes for common query patterns
- Implement caching for aggregation queries
- Use materialized views for complex correlations
- Implement pagination for all list endpoints

**Error Handling:**
- Invalid enums return 400 Bad Request
- Missing required parameters return 400 Bad Request
- Feature flag disabled returns 503 Service Unavailable

---

## UI Components

### Design Principles

1. **Neutral Language**: No judgment words like "better", "worse", "intelligent"
2. **Observational Tone**: Use "correlates with", "observed alongside", "associated with"
3. **Read-Only**: No modification capabilities
4. **Exploratory**: Support filtering, comparison, correlation discovery

### New UI Components

#### 1. DecisionExplorer Component

**Location:** `ui/components/DecisionExplorer.tsx`

**Purpose:** Visualize decision distributions and patterns

**Features:**
- **Decision Type Filter**: Dropdown to select decision type
- **Reason Code Breakdown**: Bar chart showing reason code distribution
- **Confidence Distribution**: Histogram of confidence values
- **Time Series**: Decision counts over time
- **Version Comparison**: Side-by-side decision pattern comparison

**Visualization Examples:**
- Stacked bar chart: Decision types by reason code
- Line chart: Decision frequency over time
- Pie chart: Reason code distribution for selected decision type

**No-Nos:**
- ❌ Don't label any decision as "correct" or "optimal"
- ❌ Don't suggest "improving" decisions
- ✅ Use "This decision type was observed in 42% of runs"

#### 2. QualitySignalDashboard Component

**Location:** `ui/components/QualitySignalDashboard.tsx`

**Purpose:** Visualize quality signal distributions

**Features:**
- **Signal Type Filter**: Dropdown to select signal type
- **Signal Code Breakdown**: Bar chart showing code distribution
- **True/False Rates**: Percentage visualization
- **Correlation with Outcomes**: Show signal presence alongside success/failure rates
- **Time Series**: Signal trends over time

**Visualization Examples:**
- Stacked area chart: Signal types over time
- Grouped bar chart: True/false rates by signal code
- Scatter plot: Confidence vs. signal presence

**No-Nos:**
- ❌ Don't call signals "quality scores"
- ❌ Don't aggregate into single "health" metric
- ✅ Use "This signal was present in 85% of successful runs"

#### 3. VersionComparison Component

**Location:** `ui/components/VersionComparison.tsx`

**Purpose:** Compare decision and signal patterns across versions

**Features:**
- **Version Selector**: Dropdowns for version A and version B
- **Decision Delta View**: Show decision pattern changes
- **Signal Delta View**: Show signal distribution changes
- **Outcome Correlation**: Show how deltas correlate with outcome changes
- **Drill-Down**: Link to specific runs with notable patterns

**Visualization Examples:**
- Side-by-side bar charts: Version A vs Version B decision distribution
- Delta indicators: +15% in "fresh_data_required" reason code
- Sankey diagram: Decision flow changes between versions

**No-Nos:**
- ❌ Don't label versions as "better" or "worse"
- ❌ Don't suggest automatic rollback
- ✅ Use "Version 1.1 shows 15% increase in retry_after_response signal"

#### 4. CorrelationExplorer Component

**Location:** `ui/components/CorrelationExplorer.tsx`

**Purpose:** Explore correlations between decisions/signals and outcomes

**Features:**
- **Correlation Heatmap**: Visual matrix of correlations
- **Drill-Down**: Click to see specific runs with pattern
- **Filter by Strength**: Show only correlations above threshold
- **Export**: Download correlation data for further analysis

**Visualization Examples:**
- Heatmap: Decision types vs. failure types (color = correlation strength)
- Bubble chart: Signal type vs. outcome (size = occurrence count)

**No-Nos:**
- ❌ Don't claim causation ("This decision causes failures")
- ✅ Use "This decision type is observed alongside failures in 78% of cases"

### UI Language Guidelines

**Preferred Phrasing:**
- "Observed in X% of runs"
- "Correlates with outcome Y"
- "Associated with signal Z"
- "Present alongside failures"
- "Distribution changed between versions"

**Avoid:**
- "This is the correct decision"
- "Better performance"
- "Optimal choice"
- "Agent is smarter"
- "Fix this decision"

---

## Privacy Enforcement

### Multi-Layer Validation

**Layer 1: SDK Validation**
- Check metadata keys against blocklist
- Validate string lengths (max 100 chars)
- Ensure primitive types only
- Reject before transmission

**Layer 2: API Validation**
- Pydantic validators on all Phase 2 models
- Enum strict validation
- Metadata re-validation
- Reject with 400 Bad Request

**Layer 3: Database Constraints**
- CHECK constraints on enums
- JSONB validation triggers
- Foreign key integrity
- Prevent direct DB writes

### Privacy Testing

**Required Tests:**
1. **Blocked Key Test**: Verify metadata with "prompt" key is rejected
2. **String Length Test**: Verify strings >100 chars are rejected
3. **Nested Object Test**: Verify deeply nested objects are rejected
4. **Free Text Test**: Verify long text in reason_code is rejected (must be enum)
5. **Integration Test**: Verify end-to-end privacy enforcement

### Privacy Audit

**Audit Checklist:**
- [ ] No free-text fields in schema
- [ ] All enums validated
- [ ] Metadata blocklist enforced
- [ ] String length limits enforced
- [ ] UI shows no sensitive data
- [ ] API responses contain no free text
- [ ] Database has no text columns (except enum values)

---

## Testing Strategy

### Unit Tests

**Backend Model Tests:**
- `test_decision_model_validation()`: Validate enum enforcement
- `test_signal_model_validation()`: Validate enum enforcement
- `test_metadata_privacy_rejection()`: Verify privacy violations rejected
- `test_confidence_range_validation()`: Verify 0.0-1.0 constraint
- `test_foreign_key_constraints()`: Verify relationships

**SDK Tests:**
- `test_record_decision_valid()`: Verify valid decision recorded
- `test_record_decision_invalid_type()`: Verify invalid enum rejected
- `test_record_decision_privacy_violation()`: Verify blocked metadata rejected
- `test_record_signal_valid()`: Verify valid signal recorded
- `test_phase2_optional()`: Verify Phase 1 works without Phase 2

**Pydantic Validator Tests:**
- `test_decision_type_enum_validation()`: Reject invalid decision_type
- `test_reason_code_context_validation()`: Reject invalid reason_code for type
- `test_signal_type_enum_validation()`: Reject invalid signal_type
- `test_metadata_blocklist_validation()`: Reject "prompt" key

### Integration Tests

**Full Flow Tests:**
- `test_phase1_only_ingestion()`: Phase 1 client works unchanged
- `test_phase2_ingestion_with_decisions()`: Decisions stored correctly
- `test_phase2_ingestion_with_signals()`: Signals stored correctly
- `test_phase2_query_aggregation()`: Aggregations return correct data
- `test_version_comparison()`: Comparison logic works correctly
- `test_correlation_calculation()`: Correlation queries work

**Backward Compatibility Tests:**
- `test_phase1_client_unchanged()`: Old SDK version works
- `test_phase2_disabled_flag()`: Feature flag disables Phase 2
- `test_phase1_schema_unchanged()`: Phase 1 tables not modified

### Privacy Tests

**Privacy Violation Tests:**
- `test_prompt_in_metadata_rejected()`: "prompt" key rejected at SDK
- `test_prompt_in_metadata_rejected_api()`: "prompt" key rejected at API
- `test_long_string_rejected()`: 200-char string rejected
- `test_nested_object_rejected()`: Deeply nested object rejected
- `test_reasoning_text_rejected()`: "reasoning" key rejected

**Privacy Guarantee Tests:**
- `test_no_free_text_in_database()`: Query all Phase 2 tables, verify no long strings
- `test_ui_shows_no_sensitive_data()`: Mock API responses, verify UI renders only enums
- `test_aggregation_no_metadata()`: Aggregation endpoints don't expose metadata

### Performance Tests

**Load Tests:**
- `test_ingestion_with_decisions_latency()`: Measure P95 latency increase
- `test_aggregation_query_performance()`: Verify queries under 1s
- `test_correlation_query_performance()`: Verify complex queries under 5s
- `test_high_cardinality_decisions()`: 1000 decisions per run

**Scalability Tests:**
- `test_million_decisions_storage()`: Verify database handles scale
- `test_query_performance_with_load()`: Queries performant under load

### Test Coverage Goals

- **Unit Tests**: >90% coverage
- **Integration Tests**: All critical paths covered
- **Privacy Tests**: 100% of privacy rules tested
- **Performance Tests**: P95 latency benchmarks established

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Database schema and migrations

**Tasks:**
1. Design and review schema for `agent_decisions` and `agent_quality_signals`
2. Create migration SQL files
3. Define initial enums (decision types, reason codes, signal types, signal codes)
4. Implement enum validation functions
5. Create database indexes
6. Write unit tests for schema constraints
7. Test migration on staging database

**Deliverables:**
- `db/migrations/002_phase2_schema.sql`
- `backend/enums.py` (Phase 2 enum definitions)
- Schema documentation

**Success Criteria:**
- Migration runs successfully
- Rollback works correctly
- Phase 1 schema unchanged
- All constraints enforced

### Phase 2: SDK Extensions (Weeks 3-4)

**Goal:** Extend Python SDK with optional Phase 2 APIs

**Tasks:**
1. Implement `record_decision()` method
2. Implement `record_quality_signal()` method
3. Add privacy validation function
4. Extend `AgentRunCreate` Pydantic model
5. Add SDK unit tests
6. Update SDK documentation
7. Create example scripts

**Deliverables:**
- Updated `sdk/agenttrace.py`
- `sdk/validators_phase2.py` (privacy validation)
- `examples/agent_with_decisions.py`
- `examples/agent_with_quality_signals.py`
- Updated SDK README

**Success Criteria:**
- SDK methods work correctly
- Privacy validation rejects unsafe data
- Phase 1 SDK behavior unchanged
- Examples run successfully

### Phase 3: API Extensions (Weeks 5-6)

**Goal:** Extend ingest and query APIs

**Tasks:**
1. Extend ingest API to accept Phase 2 payloads
2. Implement Phase 2 Pydantic validators
3. Implement decision aggregation endpoint
4. Implement signal aggregation endpoint
5. Implement version comparison endpoint
6. Implement correlation endpoints
7. Extend run details endpoint
8. Add API integration tests
9. Update API documentation

**Deliverables:**
- Updated `backend/ingest_api.py`
- Updated `backend/query_api.py`
- `backend/models_phase2.py` (Decision and Signal models)
- `backend/validators_phase2.py` (API validators)
- `backend/queries_phase2.py` (Query logic)
- Updated API documentation

**Success Criteria:**
- All endpoints work correctly
- Validation rejects invalid data
- Aggregations return correct results
- Performance meets benchmarks (<1s for simple queries)

### Phase 4: UI Components (Weeks 7-8)

**Goal:** Build Phase 2 visualization components

**Tasks:**
1. Implement DecisionExplorer component
2. Implement QualitySignalDashboard component
3. Implement VersionComparison component
4. Implement CorrelationExplorer component
5. Add UI integration tests
6. Update navigation and routing
7. Add loading states and error handling
8. Review UI language for neutrality

**Deliverables:**
- `ui/components/DecisionExplorer.tsx`
- `ui/components/QualitySignalDashboard.tsx`
- `ui/components/VersionComparison.tsx`
- `ui/components/CorrelationExplorer.tsx`
- Updated `ui/App.tsx` (routing)
- UI component tests

**Success Criteria:**
- All components render correctly
- Visualizations are accurate
- Language is neutral and observational
- No performance regressions

### Phase 5: Testing & Documentation (Weeks 9-10)

**Goal:** Comprehensive testing and documentation

**Tasks:**
1. Write privacy test suite
2. Write backward compatibility tests
3. Perform load testing
4. Write Phase 2 documentation
5. Create mermaid diagrams for Phase 2 flows
6. Update CONTRIBUTING.md with Phase 2 guidelines
7. Update README.md with Phase 2 features
8. Create migration guide for users

**Deliverables:**
- `tests/test_phase2_privacy.py`
- `tests/test_phase2_compatibility.py`
- `tests/test_phase2_performance.py`
- `docs/phase2-overview.md`
- `docs/phase2-decision-tracking.md`
- `docs/phase2-quality-signals.md`
- `docs/phase2-migration-guide.md`
- Updated mermaid diagrams

**Success Criteria:**
- >90% test coverage
- All privacy tests pass
- Performance benchmarks met
- Documentation complete and accurate

### Phase 6: Production Readiness (Weeks 11-12)

**Goal:** Feature flagging, rollout preparation, monitoring

**Tasks:**
1. Implement feature flag system
2. Add Phase 2 specific metrics
3. Add Phase 2 logging
4. Perform security review
5. Perform privacy audit
6. Create rollout plan
7. Prepare rollback procedure
8. Train support team

**Deliverables:**
- `backend/feature_flags.py`
- `backend/metrics_phase2.py`
- Phase 2 security review report
- Phase 2 privacy audit report
- Rollout runbook
- Rollback runbook

**Success Criteria:**
- Feature flag controls Phase 2 behavior
- Metrics track Phase 2 usage
- Security review approved
- Privacy audit passed
- Rollout plan approved

---

## Backward Compatibility

### Guarantees

**Phase 1 Clients:**
- Continue to work without any changes
- Receive same API responses (Phase 2 fields omitted)
- Experience no performance degradation
- See no schema changes

**Phase 2 Opt-In:**
- Users must explicitly call `record_decision()` and `record_quality_signal()`
- If not called, behavior identical to Phase 1
- Phase 2 API fields optional in all requests

**Feature Flag:**
- Environment variable `ENABLE_PHASE2=false` disables all Phase 2 features
- Ingest API ignores Phase 2 fields when disabled
- Query API returns 503 for Phase 2 endpoints when disabled
- SDK methods become no-ops when disabled (log warning)

### Compatibility Testing

**Test Matrix:**

| Client Version | Server Phase 2 Enabled | Expected Behavior |
|----------------|------------------------|-------------------|
| Phase 1 SDK | Yes | Works, Phase 2 ignored |
| Phase 1 SDK | No | Works, identical behavior |
| Phase 2 SDK (no calls) | Yes | Works, Phase 2 optional |
| Phase 2 SDK (no calls) | No | Works, identical behavior |
| Phase 2 SDK (with calls) | Yes | Works, Phase 2 recorded |
| Phase 2 SDK (with calls) | No | Works, Phase 2 logged but ignored |

### Migration Path

**For Existing Users:**
1. Upgrade backend (database migration runs automatically)
2. Phase 2 disabled by default (feature flag)
3. Test Phase 1 functionality unchanged
4. Enable Phase 2 feature flag
5. Upgrade SDK (optional)
6. Start using Phase 2 APIs (optional)

**No Breaking Changes:**
- No API endpoint modifications
- No response schema changes (only additions)
- No required fields added
- No behavior changes unless opted in

---

## Rollout Strategy

### Stage 1: Internal Testing (Week 13)

**Scope:** Development environment only

**Actions:**
- Enable Phase 2 on dev environment
- Internal team tests all features
- Run full test suite
- Verify metrics and logging
- Performance benchmarking

**Success Criteria:**
- All tests pass
- No regressions detected
- Performance acceptable

### Stage 2: Canary Deployment (Week 14)

**Scope:** 5% of production traffic

**Actions:**
- Deploy to production with feature flag disabled
- Enable Phase 2 for 5% of agents (canary flag)
- Monitor metrics closely
- Compare Phase 1 vs Phase 2 performance
- Collect user feedback

**Monitoring:**
- Error rates
- Latency P50, P95, P99
- Database query performance
- Privacy violation attempts

**Rollback Trigger:**
- Error rate increase >5%
- Latency increase >20%
- Privacy violation detected
- Critical bug found

### Stage 3: Gradual Rollout (Weeks 15-16)

**Scope:** 5% → 25% → 50% → 100%

**Actions:**
- Increase canary percentage weekly
- Continue monitoring
- Gather user feedback
- Fix issues as discovered

**Success Criteria per Stage:**
- Stable error rates
- No performance degradation
- Positive user feedback
- No privacy incidents

### Stage 4: General Availability (Week 17)

**Scope:** 100% availability, still opt-in

**Actions:**
- Enable Phase 2 for all agents
- Update public documentation
- Announce feature availability
- Provide migration guide
- Offer support for early adopters

**Success Metrics:**
- Adoption rate
- User satisfaction
- Feature usage patterns
- Support ticket volume

---

## Success Criteria

### Technical Success

**Phase 1 Preservation:**
- [ ] All Phase 1 tests still pass
- [ ] Phase 1 schema unchanged
- [ ] Phase 1 performance unchanged
- [ ] Phase 1 clients work without modification

**Phase 2 Functionality:**
- [ ] Decisions ingested and queryable
- [ ] Quality signals ingested and queryable
- [ ] Aggregation queries work correctly
- [ ] Version comparison works correctly
- [ ] Correlation analysis works correctly
- [ ] UI components render correctly

**Privacy & Security:**
- [ ] All privacy tests pass
- [ ] No prompts stored
- [ ] No responses stored
- [ ] No reasoning text stored
- [ ] Metadata validated at all layers
- [ ] Security review approved

**Performance:**
- [ ] Ingestion latency increase <10%
- [ ] Query latency <1s for simple queries
- [ ] Query latency <5s for complex queries
- [ ] Database handles 1M+ decisions

**Testing:**
- [ ] >90% unit test coverage
- [ ] All integration tests pass
- [ ] All privacy tests pass
- [ ] Backward compatibility verified

### Product Success

**User Value:**
- [ ] Users can answer "why did agent choose this?"
- [ ] Users can compare versions effectively
- [ ] Users can identify quality patterns
- [ ] Users can correlate decisions with outcomes

**Adoption:**
- [ ] >20% of agents use Phase 2 within 3 months
- [ ] Positive user feedback (>4/5 rating)
- [ ] <10 support tickets per week

**Documentation:**
- [ ] Complete API documentation
- [ ] Complete SDK documentation
- [ ] Migration guide published
- [ ] Example scripts available
- [ ] Mermaid diagrams updated

### Business Success

**No Negative Impact:**
- [ ] No increase in infrastructure costs >20%
- [ ] No performance complaints
- [ ] No privacy incidents
- [ ] No rollbacks required

**Positive Outcomes:**
- [ ] Enable root cause analysis for regressions
- [ ] Reduce debugging time for users
- [ ] Increase platform value proposition
- [ ] Maintain privacy-first reputation

---

## Risk Assessment & Mitigation

### Risk 1: Privacy Violation

**Risk:** Sensitive data accidentally stored

**Likelihood:** Medium
**Impact:** Critical

**Mitigation:**
- Multi-layer validation (SDK, API, DB)
- Comprehensive privacy test suite
- Metadata blocklist enforcement
- String length limits
- Privacy audit before launch
- Monitoring for violation attempts

**Rollback Plan:**
- Immediate feature flag disable
- Data purge procedure
- Incident response plan

### Risk 2: Performance Degradation

**Risk:** Phase 2 slows down ingestion or queries

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- Database indexes for common queries
- Query performance testing
- Caching for aggregations
- Materialized views for complex correlations
- Feature flag for quick disable
- Load testing before rollout

**Rollback Plan:**
- Disable Phase 2 via feature flag
- Investigate slow queries
- Optimize indexes
- Re-enable gradually

### Risk 3: Scope Creep into Optimization

**Risk:** Features drift toward behavior modification

**Likelihood:** Low
**Impact:** Critical

**Mitigation:**
- Strict adherence to claude.md guidelines
- Design review for all features
- Code review checklist
- No "auto-fix" or "suggest" features
- Language review for UI components
- Regular alignment checks

**Prevention:**
- Reject any PR that suggests optimization
- Maintain separation: observe vs. control
- Document boundary clearly

### Risk 4: Backward Compatibility Break

**Risk:** Phase 1 clients stop working

**Likelihood:** Low
**Impact:** Critical

**Mitigation:**
- Comprehensive compatibility testing
- Optional-only fields
- Feature flag default disabled
- Gradual rollout
- Version testing matrix

**Rollback Plan:**
- Immediate rollback to Phase 1
- Fix compatibility issues
- Re-test before re-deploy

### Risk 5: Enum Explosion

**Risk:** Too many enums make system unusable

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**
- Start with minimal enum set
- Add enums based on real usage
- Document enum addition process
- Allow custom enums via metadata (validated)
- Regular enum review and consolidation

**Prevention:**
- Require justification for new enums
- Review enum usage patterns
- Deprecate unused enums

---

## Metrics & Monitoring

### Phase 2 Specific Metrics

**Ingestion Metrics:**
- `phase2_decisions_ingested_total` (counter)
- `phase2_signals_ingested_total` (counter)
- `phase2_ingest_latency_seconds` (histogram)
- `phase2_privacy_violations_rejected_total` (counter)
- `phase2_invalid_enums_rejected_total` (counter)

**Query Metrics:**
- `phase2_aggregation_queries_total` (counter)
- `phase2_correlation_queries_total` (counter)
- `phase2_query_latency_seconds` (histogram)
- `phase2_query_errors_total` (counter)

**Usage Metrics:**
- `phase2_agents_using_decisions` (gauge)
- `phase2_agents_using_signals` (gauge)
- `phase2_decision_types_distribution` (histogram)
- `phase2_signal_types_distribution` (histogram)

**Health Metrics:**
- `phase2_feature_flag_enabled` (gauge)
- `phase2_database_connection_errors_total` (counter)
- `phase2_api_availability` (gauge)

### Alerting Rules

**Critical Alerts:**
- Privacy violation attempts >0 → Immediate alert
- Error rate >1% → Page on-call
- Database connection errors → Page on-call

**Warning Alerts:**
- Ingestion latency P95 >500ms → Alert team
- Query latency P95 >2s → Alert team
- Invalid enum rate >5% → Alert team

### Dashboards

**Phase 2 Overview Dashboard:**
- Total decisions/signals ingested
- Ingestion rate over time
- Query rate over time
- Error rates
- Latency percentiles

**Privacy Monitoring Dashboard:**
- Privacy violation attempts
- Blocked metadata keys
- String length violations
- Validation failures

**Usage Dashboard:**
- Agents using Phase 2
- Decision type distribution
- Signal type distribution
- Version comparison usage

---

## Appendix: Example Usage Patterns

### Example 1: Tool Selection Decision

```python
from agenttrace import AgentTracer

tracer = AgentTracer(agent_id="customer_support", agent_version="2.0.0")

with tracer.start_run() as run:
    with run.step("plan", "analyze_query") as step:
        # Agent logic determines which tool to use
        user_query = "What's my order status?"

        # Check if we have recent cached data
        cache_age_minutes = get_cache_age("order_status")

        if cache_age_minutes < 5:
            selected_tool = "use_cache"
            reason = "cached_data_fresh"
            confidence = 0.95
        else:
            selected_tool = "query_database"
            reason = "fresh_data_required"
            confidence = 0.88

        # Record the decision (explicit)
        run.record_decision(
            decision_type="tool_selection",
            selected=selected_tool,
            reason_code=reason,
            candidates=["use_cache", "query_database", "call_api"],
            confidence=confidence,
            step_id=step.step_id
        )

    with run.step("tool", selected_tool) as step:
        if selected_tool == "use_cache":
            result = get_from_cache("order_status")
        else:
            result = query_database("order_status")

        # Record quality signal
        run.record_quality_signal(
            signal_type="tool_success",
            signal_code="first_attempt",
            value=True,
            step_id=step.step_id
        )
```

### Example 2: Schema Validation Signal

```python
with tracer.start_run() as run:
    with run.step("generate", "create_response") as step:
        response = llm.generate(prompt)

        # Validate response against schema
        is_valid = validate_schema(response, expected_schema)

        # Record quality signal
        run.record_quality_signal(
            signal_type="schema_valid",
            signal_code="full_match" if is_valid else "validation_failed",
            value=is_valid,
            step_id=step.step_id,
            metadata={"schema_version": "1.2.0"}
        )
```

### Example 3: Empty Retrieval Signal

```python
with tracer.start_run() as run:
    with run.step("retrieve", "search_knowledge_base") as step:
        results = vector_search(query, top_k=10)

        # Record signal for empty retrieval
        if len(results) == 0:
            run.record_quality_signal(
                signal_type="empty_retrieval",
                signal_code="no_results",
                value=True,
                step_id=step.step_id,
                metadata={"query_length": len(query)}
            )
        else:
            run.record_quality_signal(
                signal_type="retrieval_success",
                signal_code="results_found",
                value=True,
                step_id=step.step_id,
                metadata={"result_count": len(results)}
            )
```

---

## Conclusion

This implementation plan outlines a comprehensive, privacy-safe, additive approach to extending the AgentTracer Platform with decision and quality signal tracking.

**Key Principles Maintained:**
- ✅ Strictly observational (no behavior modification)
- ✅ Additive only (Phase 1 unchanged)
- ✅ Privacy-first (no sensitive data storage)
- ✅ Explicit opt-in (all Phase 2 APIs optional)
- ✅ Backward compatible (Phase 1 clients work unchanged)

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1: Database schema design
3. Iterate based on feedback
4. Execute implementation phases sequentially

**Questions for Review:**
- Are the enum definitions comprehensive enough?
- Is the privacy validation multi-layer approach sufficient?
- Are the UI components neutral enough in language?
- Is the rollout strategy conservative enough?
- Are there additional correlation queries needed?

This plan provides a clear roadmap for Phase 2 implementation while maintaining all Phase 1 guarantees and upholding strict privacy boundaries.
