# AgentTracer Platform

## What is this?

**AgentTracer** is a privacy-safe observability platform for AI agents. It provides visibility into agent execution, decision-making, and behavioral changes without storing prompts or responses.

**What it captures:**

- **Execution:** Agent runs, ordered steps, step-level latency, semantic failures
- **Decisions:** Tool selection, retry strategies, structured reasoning codes
- **Drift:** Statistical baselines, behavioral change detection, informational alerts

**Core mental model:**

```
AgentRun
├─ AgentStep (ordered execution steps)
├─ AgentFailure (optional semantic failure)
├─ AgentDecision (optional decision points)
└─ AgentQualitySignal (optional quality indicators)
     ↓
Derived Analytics
├─ BehaviorProfile (statistical snapshot)
├─ BehaviorBaseline (immutable baseline)
└─ BehaviorDrift (detected changes)
```

AgentTracer allows engineers to reconstruct agent behavior in production, understand why agents make specific choices, and detect when behavior changes significantly over time.

## Why does it exist?

AI agents are non-deterministic, tool-driven systems that violate the assumptions of traditional observability.

**Problems agents introduce:**

- Tools time out or return malformed data
- Retries inflate latency without visibility
- Retrieval returns no results
- Behavior changes across versions without infrastructure changes
- Failures are semantic rather than infrastructural

**Traditional tools fall short:**

Traditional observability (logs, metrics, traces) shows **what was executed**, but not **why an agent behaved that way**.

| Tool Type | Limitation | AgentTracer Approach |
|-----------|-----------|---------------------|
| **Logs** | Unstructured, difficult to aggregate | Structured runs with ordered steps |
| **Metrics** | No per-run context | Full run reconstruction with steps |
| **Traces** | Execution visibility without semantic meaning | Semantic failure taxonomy |

**AgentTracer's approach:**

- Agent-native execution primitives (runs, steps, failures)
- Semantic failure classification (tool/model/retrieval/orchestration)
- Explicit retry modeling
- Privacy-first telemetry (no prompts, no responses, no PII)
- Behavioral drift detection with statistical baselines

AgentTracer makes agent behavior inspectable while maintaining strict privacy and safety boundaries.

## Who is it for?

**AgentTracer is for:**

- Engineers operating LLM-based agents in production
- Platform teams responsible for agent reliability
- Teams integrating tools, retrieval, and orchestration with agents
- Organizations that require privacy-safe observability

**Roles:**

- Backend engineers
- Infrastructure/platform engineers
- Applied AI/ML engineers

**AgentTracer is NOT for:**

- Prompt engineering workflows
- Chat transcript storage
- Prompt versioning or diffing
- Model training or fine-tuning
- Automatic agent optimization
- Reinforcement learning pipelines
- Evaluation benchmarks or grading frameworks

These exclusions are intentional design decisions, not missing features.

## How do I use it in 2 minutes?

**Start the platform:**

```bash
docker compose up -d
```

**Install SDK:**

```bash
uv pip install -e .
# Or using pip: pip install -e .
```

**Instrument your agent:**

```python
from sdk.agenttrace import AgentTracer

tracer = AgentTracer(
    agent_id="my-agent",
    agent_version="v1.0",
    environment="dev"
)

with tracer.start_run() as run:
    with run.step("plan", "analyze"):
        # Your planning logic
        pass

    with run.step("tool", "api_call"):
        # Tool invocation
        pass

    with run.step("respond", "generate"):
        # Response generation
        pass
```

**View results:**

```bash
curl http://localhost:8001/v1/runs | jq
# Or open http://localhost:3000 for UI
```

That's it. See [QUICK_START.md](./QUICK_START.md) for detailed setup, failure handling, and advanced usage.

## What problem does it NOT solve?

**AgentTracer intentionally excludes:**

**Storage and Content:**
- Raw prompts or LLM responses
- Chain-of-thought capture
- Chat transcripts
- User input or PII
- Retrieved documents

**Evaluation and Optimization:**
- Correctness evaluation or grading
- Quality scores or rankings
- Automatic agent optimization
- Agent self-modification
- Reinforcement learning
- Prescriptive recommendations

**Replay and Simulation:**
- Prompt versioning or diffing
- Execution replay
- What-if simulation

**What AgentTracer DOES provide:**

- Privacy-safe execution observability
- Semantic failure classification
- Behavioral drift detection (descriptive only, no judgment)
- Decision point observability
- Latency attribution
- Retry visibility

**Boundary:** AgentTracer observes and describes behavior. It never judges correctness, optimizes decisions, or changes agent behavior.

---

## Core Concepts

### AgentRun

A single execution of an agent, identified by:

- agent ID
- agent version
- environment
- start and end timestamps
- final status (success / failure / partial)

### AgentStep

An ordered step within an agent run, such as:

- planning
- retrieval
- tool invocation
- response generation

Each step records:

- execution order (seq)
- latency
- step type
- safe metadata only

Retries are represented as separate steps rather than overwritten attempts.

### AgentFailure

A structured, semantic failure description:

- failure type (tool / model / retrieval / orchestration)
- failure code (e.g., timeout, schema_invalid)
- optional linkage to the step that caused the failure

### AgentDecision

A structured record of a decision point where the agent selected between options:

- decision type (tool_selection, retry_strategy, response_mode, etc.)
- selected option
- structured reason code (enum-based)
- candidates considered
- optional confidence score (0.0-1.0)

Example: "Selected 'api' over 'cache' because 'fresh_data_required' (confidence: 0.85)"

### AgentQualitySignal

An atomic, factual signal correlated with outcome quality:

- signal type (schema_valid, tool_success, latency_threshold, etc.)
- signal code (specific indicator)
- boolean value (true/false)
- optional weight (importance)

Example: "Schema validation = full_match (true)" or "Tool execution = rate_limited (true)"

Quality signals are observational only - no quality scores or correctness judgments.

### BehaviorProfile

A statistical snapshot of agent behavior over a time window, aggregated from behavioral data:

- decision distributions (e.g., tool_selection: {api: 0.65, cache: 0.30})
- signal distributions (e.g., schema_valid: {full_match: 0.92, partial_match: 0.06})
- latency statistics (mean, p50, p95, p99)
- sample size (number of runs aggregated)

Profiles are used to create baselines.

### BehaviorBaseline

An immutable snapshot of expected agent behavior:

- baseline type (version-based, time-window, or manual)
- references a behavior profile
- optional human approval
- only one active baseline per (agent, version, environment)

Baselines cannot be modified after creation - ensures auditability and prevents silent baseline shifts.

### BehaviorDrift

A record of statistically significant behavioral change:

- drift type (decision, signal, or latency)
- metric (specific dimension that changed)
- baseline vs observed values
- statistical significance (p-value)
- severity (low/medium/high based on magnitude)

**Critical:** Drift is descriptive, not evaluative. Drift means "behavior changed" - NOT "agent broke" or "quality degraded". Human interpretation required.

## Architecture

**AgentTracer operates alongside the agent runtime:**

```
Client
  ↓
Agent (LLM + Tools + Orchestration)
  ↓
AgentTracer SDK (this repository)
  ↓
Ingest API
  ↓
Observability Database
  ↓
Query API / UI
```

AgentTracer observes execution but does not influence agent behavior.

**Platform components:**

- **Ingest API** (port 8000): Write-only API for telemetry ingestion
- **Query API** (port 8001): Read-only API for querying runs
- **PostgreSQL**: Persistent storage with schema validation
- **Python SDK**: Client library for instrumenting agents
- **React UI**: Dashboard for visualizing runs and failures

## Privacy-first Design

AgentTracer enforces privacy at multiple layers:

**Never stored:**
- Raw prompts
- LLM responses
- Chain-of-thought
- User input
- Retrieved documents
- PII

**Always stored:**
- Step types and names
- Latency measurements
- Failure classifications
- Safe metadata (tool names, HTTP codes, counts)

**Privacy enforcement:**
1. SDK-level metadata filtering
2. Pydantic validation with field validators
3. Database schema design (no TEXT columns for content)

## Examples

Complete usage examples in [examples/](./examples/):

1. **customer_support_agent.py** - Success case with retries
2. **agent_with_failures.py** - Demonstrates all failure types
3. **agent_with_decisions_example.py** - Includes decisions and quality signals
4. **drift_detection_example.py** - Demonstrates drift detection workflow

Run examples:
```bash
python examples/customer_support_agent.py
python examples/agent_with_failures.py
python examples/agent_with_decisions_example.py
python examples/drift_detection_example.py
```

## Documentation

See [QUICK_START.md](./QUICK_START.md) for detailed getting started guide.

See [docs/internal/](./docs/internal/) for development documentation including design principles, technical design, and development history.

## Stability and Maturity

**Status: Complete and production-ready.**

- Data schemas are stable (runs, steps, failures, decisions, signals, profiles, baselines, drift)
- SDK API is stable (backward compatible)
- Ingest and query APIs are stable
- Drift detection API complete (/v1/drift/*)
- Drift detection engine operational

All capabilities are additive - new features don't modify existing schemas. Breaking changes to core primitives are not anticipated.

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL 15
- **Statistics**: NumPy, SciPy (drift detection)
- **UI**: React 18, TypeScript, Tailwind CSS, Vite
- **Deployment**: Docker, Docker Compose
- **SDK**: Python with httpx
- **Package Management**: uv (modern Python package manager)

## License

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

---

**AgentTracer prioritizes clarity, safety, and correctness over breadth of features.**

> Understanding agent behavior is a prerequisite to improving it.
