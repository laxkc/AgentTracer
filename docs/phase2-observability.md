# Phase 2: Decision & Quality Observability

This document describes Phase 2 features of the AgentTracer Platform, which extend Phase 1 execution observability with structured decision tracking and quality signal capture.

## Table of Contents
- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Agent Decisions](#agent-decisions)
- [Quality Signals](#quality-signals)
- [Privacy Enforcement](#privacy-enforcement)
- [SDK Usage](#sdk-usage)
- [Data Model](#data-model)
- [UI Components](#ui-components)

---

## Overview

### Phase 2 Goal

**Make agent decisions, quality signals, and outcomes observable without changing agent behavior.**

Phase 2 is strictly observational - it records what agents do, not what they should do.

### Key Principles

1. **Observational Only** - No optimization, tuning, or behavior modification
2. **Structured Data** - Enum-based reason codes, not free-form text
3. **Privacy-Safe** - No prompts, responses, or reasoning text
4. **Additive Architecture** - Phase 1 unchanged, Phase 2 optional
5. **Neutral Language** - "Correlated with", "associated with", not "better" or "worse"

---

## Core Concepts

### AgentDecision

A structured record of a decision point where the agent selected between multiple options.

**What it captures:**
- **decision_type**: Category of decision (tool_selection, retry_strategy, etc.)
- **selected**: What option was chosen
- **reason_code**: Structured reason (enum-based)
- **candidates**: What options were considered
- **confidence**: Optional confidence score (0.0-1.0)

**What it does NOT capture:**
- Free-form explanations
- Chain-of-thought reasoning
- Prompt text
- Response text

### AgentQualitySignal

An atomic, factual signal correlated with outcome quality.

**What it captures:**
- **signal_type**: Category of signal (schema_valid, tool_success, etc.)
- **signal_code**: Specific signal (first_attempt, rate_limited, etc.)
- **value**: Boolean indicator (true/false)
- **weight**: Optional importance weight (0.0-1.0)

**What it does NOT capture:**
- Quality scores
- Correctness judgments
- Optimization suggestions

---

## Agent Decisions

### Decision Types

| Type | Description | Example Use Cases |
|------|-------------|-------------------|
| `tool_selection` | Choosing which tool to use | API vs cache, search vs direct lookup |
| `retrieval_strategy` | Choosing retrieval method | Vector search vs keyword, semantic vs lexical |
| `response_mode` | Choosing response format | Streaming vs batch, verbose vs concise |
| `retry_strategy` | Deciding whether to retry | Retry on failure, backoff strategy |
| `orchestration_path` | Choosing execution path | Sequential vs parallel, single vs multi-step |

### Reason Codes

Reason codes are structured, enum-based explanations for decisions.

**Tool Selection Reasons:**
- `fresh_data_required` - Need current data
- `cached_data_sufficient` - Cache is valid
- `cost_optimization` - Minimize API costs
- `latency_optimization` - Minimize response time

**Retry Strategy Reasons:**
- `rate_limit_encountered` - Hit rate limit
- `transient_error` - Temporary failure
- `timeout_exceeded` - Operation timed out
- `max_retries_reached` - Give up after max attempts

**Response Mode Reasons:**
- `streaming_preferred` - User wants real-time updates
- `batch_preferred` - Complete response preferred
- `token_limit_exceeded` - Too large for streaming

### Example: Recording a Decision

```python
with tracer.start_run() as run:
    with run.step("tool", "fetch_data") as step:
        # Make decision
        if cache_age_minutes < 5:
            selected = "cache"
            reason = "cached_data_sufficient"
            confidence = 0.95
        else:
            selected = "api"
            reason = "fresh_data_required"
            confidence = 0.85

        # Record decision
        run.record_decision(
            decision_type="tool_selection",
            selected=selected,
            reason_code=reason,
            candidates=["cache", "api", "database"],
            confidence=confidence,
            step_id=step.step_id,
            metadata={"cache_age_minutes": cache_age_minutes}
        )
```

---

## Quality Signals

### Signal Types

| Type | Description | Example Signals |
|------|-------------|-----------------|
| `schema_valid` | Schema validation result | full_match, partial_match, validation_failed |
| `empty_retrieval` | No results found | no_results, empty_response |
| `tool_success` | Tool executed successfully | first_attempt, after_retry |
| `tool_failure` | Tool execution failed | rate_limited, timeout, invalid_input |
| `retry_occurred` | Retry was needed | single_retry, multiple_retries |
| `latency_threshold` | Latency comparison | under_threshold, over_threshold |
| `token_usage` | Token consumption level | within_budget, over_budget |

### Signal Codes

Signal codes are specific indicators within each signal type.

**Schema Valid Signals:**
- `full_match` - Complete schema match
- `partial_match` - Some fields missing
- `validation_failed` - Schema validation failed

**Tool Success Signals:**
- `first_attempt` - Succeeded immediately
- `after_retry` - Succeeded after retry
- `fallback_used` - Fallback mechanism succeeded

**Tool Failure Signals:**
- `rate_limited` - Hit API rate limit
- `timeout` - Request timed out
- `invalid_input` - Bad request
- `unauthorized` - Auth failure

### Example: Recording Quality Signals

```python
with tracer.start_run() as run:
    with run.step("retrieve", "search_docs") as step:
        # Execute retrieval
        results = search_index(query)

        # Record empty retrieval signal
        if len(results) == 0:
            run.record_quality_signal(
                signal_type="empty_retrieval",
                signal_code="no_results",
                value=True,
                step_id=step.step_id
            )
        else:
            # Record success signal
            run.record_quality_signal(
                signal_type="tool_success",
                signal_code="first_attempt",
                value=True,
                step_id=step.step_id,
                metadata={"result_count": len(results)}
            )

        # Validate schema
        is_valid = validate_schema(results)
        run.record_quality_signal(
            signal_type="schema_valid",
            signal_code="full_match" if is_valid else "validation_failed",
            value=is_valid,
            weight=0.9,
            step_id=step.step_id
        )
```

---

## Privacy Enforcement

Phase 2 enforces privacy at multiple layers to prevent sensitive data leakage.

### Blocked Metadata Keys

The following keys are blocked in decision and signal metadata:

- `prompt`
- `response`
- `reasoning`
- `thought`
- `message`
- `content`
- `text`
- `output`
- `input`
- `chain_of_thought`
- `explanation`
- `rationale`

### Validation Layers

**1. SDK Layer** (`sdk/agenttrace.py`)
- Validates metadata keys before sending
- Blocks sensitive keys
- Truncates long strings (100 char limit)
- Only allows primitive types (str, int, float, bool)

**2. API Layer** (`backend/models.py`)
- Pydantic validators reject sensitive keys
- Enum validation for decision/signal types
- Type coercion and validation

**3. Database Layer** (`db/migrations/002_phase2_schema.sql`)
- Trigger functions validate metadata on INSERT/UPDATE
- Raises exception if blocked keys found
- Last line of defense

### Example: Privacy Validation

```python
# ✅ ALLOWED
run.record_decision(
    decision_type="tool_selection",
    selected="api",
    reason_code="fresh_data_required",
    metadata={"cache_age_minutes": 12}  # Safe numeric data
)

# ❌ REJECTED - Contains "prompt" key
run.record_decision(
    decision_type="tool_selection",
    selected="api",
    reason_code="fresh_data_required",
    metadata={"prompt": "What is the weather?"}  # BLOCKED
)

# ❌ REJECTED - Value is not a primitive
run.record_decision(
    decision_type="tool_selection",
    selected="api",
    reason_code="fresh_data_required",
    metadata={"config": {"key": "value"}}  # BLOCKED - nested object
)
```

---

## SDK Usage

### Complete Example

```python
from sdk.agenttrace import AgentTracer

tracer = AgentTracer(
    agent_id="customer_support_agent",
    agent_version="2.0.0",
    api_url="http://localhost:8000"
)

with tracer.start_run() as run:
    # Step 1: Decide on data source
    with run.step("plan", "choose_source") as step:
        cache_age = get_cache_age()

        if cache_age < 5:
            source = "cache"
            reason = "cached_data_sufficient"
            confidence = 0.95
        else:
            source = "api"
            reason = "fresh_data_required"
            confidence = 0.85

        # Record decision
        run.record_decision(
            decision_type="tool_selection",
            selected=source,
            reason_code=reason,
            candidates=["cache", "api"],
            confidence=confidence,
            step_id=step.step_id,
            metadata={"cache_age_minutes": cache_age}
        )

    # Step 2: Fetch data
    with run.step("tool", "fetch_data") as step:
        try:
            data = fetch_from_source(source)

            # Record success
            run.record_quality_signal(
                signal_type="tool_success",
                signal_code="first_attempt",
                value=True,
                step_id=step.step_id
            )
        except RateLimitError:
            # Record failure
            run.record_quality_signal(
                signal_type="tool_failure",
                signal_code="rate_limited",
                value=True,
                step_id=step.step_id
            )

            # Decide to retry
            run.record_decision(
                decision_type="retry_strategy",
                selected="retry",
                reason_code="rate_limit_encountered",
                confidence=0.8,
                step_id=step.step_id
            )

    # Step 3: Validate response
    with run.step("validate", "check_schema") as step:
        is_valid = validate_schema(data)

        run.record_quality_signal(
            signal_type="schema_valid",
            signal_code="full_match" if is_valid else "validation_failed",
            value=is_valid,
            weight=0.9,
            step_id=step.step_id
        )
```

---

## Data Model

### Database Schema

**agent_decisions** table:
```sql
CREATE TABLE agent_decisions (
    decision_id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(step_id) ON DELETE CASCADE,
    decision_type VARCHAR(100) NOT NULL,
    selected VARCHAR(200) NOT NULL,
    reason_code VARCHAR(100) NOT NULL,
    confidence REAL CHECK (confidence BETWEEN 0.0 AND 1.0),
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_run_id ON agent_decisions(run_id);
CREATE INDEX idx_decisions_step_id ON agent_decisions(step_id);
CREATE INDEX idx_decisions_type ON agent_decisions(decision_type);
CREATE INDEX idx_decisions_reason ON agent_decisions(reason_code);
```

**agent_quality_signals** table:
```sql
CREATE TABLE agent_quality_signals (
    signal_id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(step_id) ON DELETE CASCADE,
    signal_type VARCHAR(100) NOT NULL,
    signal_code VARCHAR(100) NOT NULL,
    value BOOLEAN NOT NULL,
    weight REAL CHECK (weight BETWEEN 0.0 AND 1.0),
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_run_id ON agent_quality_signals(run_id);
CREATE INDEX idx_signals_step_id ON agent_quality_signals(step_id);
CREATE INDEX idx_signals_type ON agent_quality_signals(signal_type);
CREATE INDEX idx_signals_code ON agent_quality_signals(signal_code);
```

### Relationships

```
AgentRun (Phase 1)
 ├─ AgentStep (Phase 1)
 ├─ AgentFailure (Phase 1)
 ├─ AgentDecision (Phase 2, optional)
 └─ AgentQualitySignal (Phase 2, optional)
```

---

## UI Components

### DecisionsList Component

Displays agent decisions in a structured, neutral format.

**Features:**
- Decision type badges with color coding
- Confidence indicators
- Candidate options visualization
- Reason code display
- Observational language only

**Design Principles:**
- No quality judgments
- Neutral tone
- Factual presentation
- "Correlated with" language

### QualitySignalsList Component

Displays quality signals grouped by type.

**Features:**
- Signal type grouping
- Boolean value indicators
- Weight display
- Summary statistics
- Metadata context

**Design Principles:**
- Atomic signal presentation
- No composite scores
- No correctness judgments
- Factual indicators only

### Example UI Flow

1. User views run in RunDetail page
2. If Phase 2 data exists, "Phase 2 Data" badge shown
3. DecisionsList shows all decision points
4. QualitySignalsList shows all quality signals
5. Both components use neutral, observational language
6. Footer notes clarify observational nature

---

## Best Practices

### When to Record Decisions

✅ **DO** record decisions when:
- Agent chooses between multiple options
- Decision has structured reasoning
- Options are well-defined
- Reason can be expressed as enum

❌ **DON'T** record decisions when:
- Only one option available
- Decision is trivial/obvious
- Reasoning is complex/unstructured
- Would expose sensitive data

### When to Record Quality Signals

✅ **DO** record signals when:
- Observable, factual event occurs
- Signal is atomic and specific
- Signal type is well-defined
- Value is boolean or numeric

❌ **DON'T** record signals when:
- Signal requires judgment
- Signal is composite
- Signal value is subjective
- Would expose sensitive data

### Privacy Checklist

Before recording Phase 2 data:
- ☐ No prompts or responses
- ☐ No reasoning or chain-of-thought
- ☐ Only enum-based codes
- ☐ Metadata uses safe keys
- ☐ Values are primitives only
- ☐ String length under 100 chars

---

## Migration from Phase 1

Phase 2 is fully backward compatible with Phase 1:

1. **No breaking changes** - Phase 1 code works unchanged
2. **Optional adoption** - Use Phase 2 features when ready
3. **Gradual migration** - Add decisions/signals incrementally
4. **Fail-safe** - Phase 2 errors don't crash agent
5. **Separate tables** - Phase 1 data unchanged

### Migration Steps

1. **Update SDK** - Pull latest `sdk/agenttrace.py`
2. **Add enum definitions** - Review `backend/enums.py`
3. **Instrument decisions** - Add `record_decision()` calls
4. **Instrument signals** - Add `record_quality_signal()` calls
5. **Test privacy** - Verify no sensitive data logged
6. **Deploy** - Roll out to production

---

## Support & Resources

- **Enums Reference**: See `backend/enums.py` for all decision types, reason codes, and signal types
- **Examples**: See `examples/agent_with_phase2.py` for complete usage examples
- **Claude Guide**: See `CLAUDE.md` for implementation guidelines
- **Database Schema**: See `db/migrations/002_phase2_schema.sql` for full schema

## Phase 2 Design Doc

For detailed design rationale and architecture decisions, see `design_doc_template.md`.
