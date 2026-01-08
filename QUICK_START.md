# Quick Start Guide — AgentTracer Platform

Get up and running in 5 minutes!

## Prerequisites

- Python 3.10+
- PostgreSQL (or Docker)
- Git

## Option 1: Docker (Recommended)

### Step 1: Start Everything

```bash
# Clone and navigate
cd testing

# Start all services
docker compose up -d

# Wait for services to be healthy (30 seconds)
docker compose ps
```

### Step 2: Verify Setup

```bash
# Check ingest API
curl http://localhost:8000/health

# Check query API
curl http://localhost:8001/health

# Expected: {"status": "healthy", ...}
```

### Step 3: Run Example

```bash
# Install Python dependencies (for SDK)
uv pip install -e .
# Or using pip: pip install -e .

# Run example agent
python examples/customer_support_agent.py
```

### Step 4: Query Results

```bash
# List all runs
curl http://localhost:8001/v1/runs | jq

# Get statistics
curl http://localhost:8001/v1/stats | jq

# Get specific run (copy run_id from list)
curl http://localhost:8001/v1/runs/{run_id} | jq
```

**That's it!**

---

## Option 2: Local Setup (No Docker)

### Step 1: Database Setup

```bash
# Create database
createdb agent_observability

# Apply schema
./server/db/setup.sh

# Or manually:
psql agent_observability < server/db/schema.sql
```

### Step 2: Start APIs

**Terminal 1 - Ingest API:**
```bash
# Install dependencies with uv (recommended)
uv pip install -e .
# Or using pip: pip install -e .

python -m server.ingest_api
# Runs on http://localhost:8000
```

**Terminal 2 - Query API:**
```bash
python -m server.query_api
# Runs on http://localhost:8001
```

### Step 3: Run Example

**Terminal 3:**
```bash
python examples/customer_support_agent.py
```

---

## Using the SDK in Your Agent

### Minimal Example

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
    with run.step("plan", "analyze_input"):
        # Your planning logic
        result = analyze_input(user_query)

    # Step 2: Tool call with retry
    for attempt in range(3):
        with run.step("tool", "call_api") as step:
            step.add_metadata({"attempt": attempt + 1})
            try:
                data = call_external_api()
                step.add_metadata({"http_status": 200})
                break
            except Exception as e:
                if attempt == 2:  # Last attempt
                    run.record_failure(
                        failure_type="tool",
                        failure_code="timeout",
                        message=f"API failed after 3 attempts"
                    )

    # Step 3: Response
    with run.step("respond", "generate_response") as step:
        response = generate_response(data)
        step.add_metadata({"response_length": len(response)})
```

### What Gets Captured

**Captured:**
- Run start/end times
- Step sequence and timing
- Retry attempts (as separate steps)
- Failure classification
- Safe metadata (tool names, codes, counts)

**NOT Captured:**
- Prompts or responses
- User input
- Retrieved documents
- Chain-of-thought

---

## Common Tasks

### View All Runs

```bash
curl http://localhost:8001/v1/runs
```

### Filter by Agent

```bash
curl "http://localhost:8001/v1/runs?agent_id=my_agent"
```

### Filter by Status

```bash
curl "http://localhost:8001/v1/runs?status=failure"
```

### Get Statistics

```bash
curl http://localhost:8001/v1/stats
```

### Get Run Details

```bash
# Replace {run_id} with actual UUID
curl http://localhost:8001/v1/runs/{run_id}
```

---

## Run Tests

```bash
# Install test dependencies with uv (recommended)
uv pip install -e ".[dev]"
# Or using pip: pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_sdk.py -v

# Run with coverage
pytest tests/ -v --cov=server --cov=sdk
```

---

## Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Or for local:
pg_isready

# Restart database
docker compose restart postgres
```

### API Not Responding

```bash
# Check API health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Check logs
docker compose logs ingest_api
docker compose logs query_api

# Restart APIs
docker compose restart ingest_api query_api
```

### Import Errors

```bash
# Make sure you're in the project root
cd testing

# Install dependencies with uv (recommended)
uv pip install -e .
# Or using pip: pip install -e .

# Set PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### No Data Showing

```bash
# Check if runs exist
curl http://localhost:8001/v1/runs

# Load seed data
psql agent_observability < server/db/seed.sql

# Run example again
python examples/customer_support_agent.py
```

---

## Next Steps

1. **Read Full Docs:** See `README.md`
2. **Integrate Your Agent:** Modify SDK example above
3. **Build UI:** Use React components in `ui/src/components/`

---

## Quick Reference

| Task | Command |
|------|---------|
| Start all services | `docker compose up -d` |
| Stop all services | `docker compose down` |
| View logs | `docker compose logs -f` |
| Run tests | `pytest tests/ -v` |
| Apply schema | `./server/db/setup.sh` |
| Load sample data | `psql agent_observability < server/db/seed.sql` |
| Check health | `curl http://localhost:8000/health` |

---

## API Endpoints Summary

### Ingest API (`:8000`)
- `POST /v1/runs` - Ingest run telemetry
- `GET /health` - Health check
- `GET /metrics` - Metrics

### Query API (`:8001`)
- `GET /v1/runs` - List runs (with filters)
- `GET /v1/runs/{run_id}` - Get specific run
- `GET /v1/runs/{run_id}/steps` - Get run steps
- `GET /v1/runs/{run_id}/failures` - Get run failures
- `GET /v1/stats` - Aggregated statistics
- `GET /health` - Health check

---

**Need Help?** Check `README.md` for complete documentation.
