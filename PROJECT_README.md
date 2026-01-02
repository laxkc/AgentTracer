# AgentTracer Platform — Phase 1

> **Make AI agent behavior visible, debuggable, and measurable** in production.

## Overview

This is a **Phase-1 MVP** of an AgentTracer Platform that captures structured agent telemetry without storing sensitive data.

### What This System Does

- ✅ Captures agent runs with ordered steps
- ✅ Measures step-level latency
- ✅ Classifies failures semantically (tool/model/retrieval/orchestration)
- ✅ Provides query API for run inspection
- ✅ **Privacy-by-default**: No prompts, responses, or PII stored

### What This System Does NOT Do

- ❌ Store raw prompts or LLM responses
- ❌ Store chain-of-thought reasoning
- ❌ Perform automatic quality evaluation
- ❌ Re-execute or replay agent logic

## Architecture

```
┌─────────────────┐
│  Agent SDK      │  ← Your agent code
│  (agenttrace.py)│
└────────┬────────┘
         │ HTTPS/JSON
         ▼
┌─────────────────┐     ┌──────────────┐
│  Ingest API     │────▶│  PostgreSQL  │
│  (FastAPI)      │     │              │
└─────────────────┘     └──────┬───────┘
                               │
┌─────────────────┐            │
│  Query API      │◀───────────┘
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  UI (Future)    │
└─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL
- Docker (optional)

### 1. Clone and Install

```bash
cd testing

# Install dependencies
pip install -r requirements.txt
```

### 2. Start PostgreSQL

**Option A: Docker Compose (Recommended)**

```bash
docker-compose up -d
```

**Option B: Local PostgreSQL**

```bash
createdb agent_observability
psql agent_observability < db/schema.sql
```

### 3. Start the APIs

**Terminal 1: Ingest API**
```bash
python -m backend.ingest_api
# Runs on http://localhost:8000
```

**Terminal 2: Query API**
```bash
python -m backend.query_api
# Runs on http://localhost:8001
```

### 4. Run Example Agent

```bash
python examples/customer_support_agent.py
```

### 5. Query the Data

```bash
# List all runs
curl http://localhost:8001/v1/runs

# Get a specific run
curl http://localhost:8001/v1/runs/{run_id}

# Get statistics
curl http://localhost:8001/v1/stats
```

## SDK Usage

### Basic Example

```python
from sdk.agenttrace import AgentTracer

# Initialize tracer
tracer = AgentTracer(
    agent_id="my_agent",
    agent_version="1.0.0",
    api_url="http://localhost:8000"
)

# Capture a run
with tracer.start_run() as run:
    # Step 1: Planning
    with run.step("plan", "analyze_query"):
        # Your planning logic
        pass

    # Step 2: Retrieval
    with run.step("retrieve", "search_kb") as step:
        # Your retrieval logic
        step.add_metadata({"result_count": 10})

    # Step 3: Tool call with retries
    for attempt in range(3):
        with run.step("tool", "call_api") as step:
            step.add_metadata({"attempt": attempt + 1})
            try:
                # Your tool logic
                break
            except Exception:
                if attempt == 2:
                    run.record_failure(
                        failure_type="tool",
                        failure_code="timeout",
                        message="API call failed after 3 attempts"
                    )
```

## Core Concepts

### AgentRun
- One execution of an agent from start to finish
- Has status: `success`, `failure`, or `partial`
- Contains ordered steps and optional failure

### AgentStep
- One atomic step in the agent lifecycle
- Types: `plan`, `retrieve`, `tool`, `respond`, `other`
- Tracks latency in milliseconds
- Contains safe metadata only (no prompts/responses)

### AgentFailure
- Semantic failure classification
- Types: `tool`, `model`, `retrieval`, `orchestration`
- Codes: `timeout`, `schema_invalid`, `empty_retrieval`, etc.

## Privacy Guarantees (Phase-1)

### ✅ Allowed to Store
- Tool names
- HTTP status codes
- Retry counts
- Latency measurements
- Numeric metadata
- Enum/string labels

### ❌ Forbidden to Store
- Raw prompts
- Raw LLM responses
- Retrieved documents
- User PII
- Chain-of-thought reasoning

## API Endpoints

### Ingest API (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/runs` | POST | Ingest agent run telemetry |
| `/health` | GET | Health check |
| `/metrics` | GET | Internal metrics |

### Query API (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/runs` | GET | List runs with filters |
| `/v1/runs/{run_id}` | GET | Get specific run |
| `/v1/runs/{run_id}/steps` | GET | Get run steps |
| `/v1/runs/{run_id}/failures` | GET | Get run failures |
| `/v1/stats` | GET | Aggregated statistics |
| `/health` | GET | Health check |

## Testing

```bash
# Run unit tests
pytest tests/test_sdk.py -v

# Run integration tests (requires APIs running)
pytest tests/test_sdk.py -v -m integration
```

## Development

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy backend sdk
```

## Project Structure

```
.
├── backend/               # FastAPI backend
│   ├── ingest_api.py     # Write-only ingest API
│   ├── query_api.py      # Read-only query API
│   └── models.py         # SQLAlchemy + Pydantic models
├── sdk/                   # Python SDK
│   ├── agenttrace.py     # Tracer + context managers
│   └── telemetry.py      # Async sender (future)
├── db/                    # Database
│   └── schema.sql        # PostgreSQL schema
├── tests/                 # Test suite
│   └── test_sdk.py       # SDK unit tests
├── examples/              # Example integrations
│   └── customer_support_agent.py
├── ui/                    # UI components (future)
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker setup
└── PROJECT_README.md     # This file
```

## Phase-1 Constraints

This is **Phase-1 MVP** with the following hard constraints:

1. **Privacy-by-default**: No prompts, responses, or PII
2. **No automatic evaluation**: Manual interpretation required
3. **No replay**: Cannot re-execute agent logic
4. **PostgreSQL only**: Scalability limits

## Future Phases

### Phase-2 (Planned)
- Reasoning summaries (privacy-safe)
- Version diffing
- Replay with mocked tools
- Hosted SaaS

### Phase-3 (Planned)
- Evaluation pipelines
- Multi-region deployment
- Advanced analytics

---

**Phase-1 Goal**: Make agent behavior visible in under 60 seconds without storing sensitive data.
