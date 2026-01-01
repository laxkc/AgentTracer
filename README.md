# AgentTracer - Phase 1

## Overview

This repository contains **Phase 1 of AgentTracer**, an agent observability platform. AgentTracer offers **structured, privacy-safe observability for AI agents** by capturing agent runs, ordered execution steps, and semantic failure details. **Phase 1 is limited to execution visibility and does not address** decision optimization or evaluation.

## What is this?

**AgentTracer** is an observability platform for AI agents. It records:

- each agent execution ("run")
- the ordered sequence of steps within that run
- step-level latency
- retries as first-class events
- semantic failure classifications

It allows engineers to **reconstruct and inspect agent behavior in production environments.**

## What problem does it solve?

AI agents can fail in ways that traditional observability tools do not explain:

- tools time out or return malformed data
- retries inflate latency without visibility
- retrieval returns no results
- agent behavior changes across versions without infrastructure changes
- failures are semantic rather than infrastructural

Existing tools, such as logs, metrics, and traces, indicate **what was executed**, but not **why an agent behaved as it did**. AgentTracer helps engineers to:

- identify where an agent failed
- understand which step caused the failure
- attribute latency to specific agent actions
- compare behavior across agent versions

## Who is this for?

AgentTracer is intended for:

- engineers operating LLM-based agents in production
- platform teams responsible for agent reliability
- teams integrating tools, retrieval, and orchestration with agents
- organizations that require privacy-safe observability

AgentTracer is also suitable for:

- backend engineers
- infra / platform engineers
- Applied AI / ML engineers

## Who is this not for?

AgentTracer is **not** intended for:

- prompt engineering workflows
- chat transcript storage
- prompt versioning or diffing
- model training or fine-tuning
- automatic agent optimization
- reinforcement learning pipelines
- evaluation benchmarks or grading frameworks

These areas are **explicitly out of scope for Phase 1**.

## Why does this exist?

AI agents are **non-deterministic, tool-driven systems**. Traditional observability assumes:

- deterministic code paths
- known failure modes

Agents violate these assumptions:

- decisions emerge from model inference
- failures are often semantic
- identical inputs may produce different behaviors
- latency is influenced by reasoning and retries

AgentTracer is designed to **make agent behavior inspectable** while maintaining safety and privacy.

## Core mental model

AgentTracer is built around a **minimal, explicit execution model**:

```
AgentRun
├─ AgentStep (ordered)
└─ AgentFailure (optional)
```

- **AgentRun** represents a single execution attempt
- **AgentStep** represents one action taken by the agent
- **AgentFailure** represents the semantic reason a run failed

This model is **stable and intentionally constrained.**

## Main concepts

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

Retries are represented as **separate steps rather than** overwritten attempts.

### AgentFailure

A structured, semantic failure description:

- failure type (tool / model / retrieval / orchestration)
- failure code (e.g., timeout, schema_invalid)
- optional linkage to the step that caused the failure

## Minimal usage

### Instrumenting an agent (Python)

```python
from sdk.agenttrace import AgentTracer

tracer = AgentTracer(
    agent_id="support-agent",
    agent_version="v1.0.0",
    environment="production",
    api_url="http://localhost:8000"
)

with tracer.start_run() as run:
    with run.step("plan", "analyze_query"):
        # Your planning logic
        pass

    with run.step("tool", "billing_api"):
        # Tool call logic
        pass

    with run.step("respond", "generate_response"):
        # Response generation
        pass
```

- No changes to prompts are required
- No model-specific logic is introduced

### Handling failures

```python
with tracer.start_run() as run:
    with run.step("plan", "analyze"):
        pass

    try:
        with run.step("tool", "external_api"):
            result = call_external_api()
    except TimeoutError:
        run.record_failure(
            failure_type="tool",
            failure_code="timeout",
            message="External API timeout after 30s"
        )
        return
```

## Where does this fit in a system

AgentTracer operates **alongside the agent runtime**:

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

AgentTracer **observes execution** but does **not influence agent behavior**.

## Quick Start

### 1. Start the platform

```bash
# Clone the repository
git clone <repository-url>
cd testing

# Start all services with Docker Compose
docker compose up -d

# Verify services are running
curl http://localhost:8000/health  # Ingest API
curl http://localhost:8001/health  # Query API
```

### 2. Run example agent

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run example with instrumentation
PYTHONPATH=. python examples/customer_support_agent.py
```

### 3. View telemetry

```bash
# Query runs via API
curl http://localhost:8001/v1/runs | jq

# Get statistics
curl http://localhost:8001/v1/stats | jq

# Or view in UI (if running)
open http://localhost:3000
```

See [QUICK_START.md](./QUICK_START.md) for detailed instructions.

## Architecture

The platform consists of:

- **Ingest API** (port 8000): Write-only API for telemetry ingestion
- **Query API** (port 8001): Read-only API for querying runs
- **PostgreSQL**: Persistent storage with schema validation
- **Python SDK**: Client library for instrumenting agents
- **React UI**: Dashboard for visualizing runs and failures

See [docs/architecture.md](./docs/architecture.md) for detailed architecture documentation.

## Privacy-first design

AgentTracer enforces privacy at multiple layers:

**Never stored:**
- ❌ Raw prompts
- ❌ LLM responses
- ❌ Chain-of-thought
- ❌ User input
- ❌ Retrieved documents
- ❌ PII

**Always stored:**
- ✅ Step types and names
- ✅ Latency measurements
- ✅ Failure classifications
- ✅ Safe metadata (tool names, HTTP codes, counts)

Privacy is enforced through:
1. SDK-level metadata filtering
2. Pydantic validation with field validators
3. Database schema design (no TEXT columns for content)

See [docs/data-flow.md](./docs/data-flow.md) for privacy enforcement details.

## What this intentionally does NOT do

Phase 1 intentionally excludes:

- storage of prompts or LLM outputs
- chain-of-thought capture
- correctness evaluation
- replay or simulation
- agent self-modification
- automated optimization

These exclusions are intentional **design decisions**, not missing features.

## How does this differ from existing tools?

| Tool Type | Limitation | AgentTracer Approach |
|-----------|-----------|---------------------|
| **Logs** | Unstructured, difficult to aggregate | Structured runs with ordered steps |
| **Metrics** | No per-run context | Full run reconstruction with steps |
| **Traces** | Execution visibility without semantic meaning | Semantic failure taxonomy |
| **Prompt tools** | Text-focused, not runtime-focused | Privacy-safe execution observability |

AgentTracer introduces:

- agent-native execution primitives
- semantic failure classification
- explicit retry modeling
- privacy-first telemetry

## Documentation

Comprehensive documentation available in [docs/](./docs/):

- [Architecture](./docs/architecture.md) - System components and design
- [Data Flow](./docs/data-flow.md) - How telemetry flows through the system
- [Failure Handling](./docs/failure-handling.md) - Failure taxonomy and classification
- [Deployment](./docs/deployment.md) - Docker architecture and deployment
- [API Sequences](./docs/api-sequences.md) - Detailed API interactions
- [Component Responsibilities](./docs/component-responsibility.md) - Separation of concerns

## Examples

Two complete examples are provided:

1. **customer_support_agent.py** - Success case with retries
2. **agent_with_failures.py** - Demonstrates all failure types

Run examples:
```bash
PYTHONPATH=. python examples/customer_support_agent.py
PYTHONPATH=. python examples/agent_with_failures.py
```

## Stability and maturity

**Phase 1 status: Stable and production-ready foundation.**

- Data schema is stable
- SDK API is stable
- Ingest and query APIs are stable

Future phases will add functionality without disrupting existing features. Breaking changes to Phase 1 primitives are **not anticipated.**

## Project scope summary

Phase 1 provides:

- execution visibility
- latency attribution
- failure understanding

It does **not** attempt to:

- judge correctness
- optimize decisions
- change agent behavior

These concerns are intentionally deferred.

## Technology Stack

- **Backend**: Python 3.10, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL 15
- **UI**: React 18, TypeScript, Tailwind CSS, Vite
- **Deployment**: Docker, Docker Compose
- **SDK**: Python with httpx

## License and contribution

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

For contribution guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Closing note

AgentTracer prioritizes **clarity, safety, and correctness** over breadth of features.

> **Understanding agent behavior is a prerequisite to improving it.**

---

Built with [Claude Code](https://claude.com/claude-code)
