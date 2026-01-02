# API Sequence Diagrams

This document provides detailed sequence diagrams for all API operations in the AgentTracer Platform.

## Table of Contents
- [Run Ingestion Sequence](#run-ingestion-sequence)
- [Run Query Sequence](#run-query-sequence)
- [Stats Aggregation Sequence](#stats-aggregation-sequence)
- [Run Detail Sequence](#run-detail-sequence)

---

## Run Ingestion Sequence

Complete sequence for ingesting an agent run via the Ingest API.

```mermaid
sequenceDiagram
    participant Agent as Agent Application
    participant SDK as Python SDK
    participant IngestAPI as Ingest API
    participant Pydantic as Pydantic Validator
    participant ORM as SQLAlchemy ORM
    participant DB as PostgreSQL

    Agent->>SDK: with tracer.start_run() as run
    activate SDK
    SDK->>SDK: Create RunContext<br/>Generate run_id UUID<br/>Capture started_at

    Agent->>SDK: with run.step("plan", "analyze")
    SDK->>SDK: Create StepContext<br/>Generate step_id UUID<br/>Capture started_at

    Agent->>Agent: Execute step logic
    Agent->>SDK: Step exits (__exit__)
    SDK->>SDK: Capture ended_at<br/>Calculate latency_ms<br/>Store in run._steps

    Agent->>SDK: with run.step("tool", "api_call")
    SDK->>SDK: Create StepContext (seq=1)
    Agent->>Agent: API call fails (Exception)
    Agent->>SDK: run.record_failure(type, code, message)
    SDK->>SDK: Create failure object<br/>Store in run._failure<br/>Set status="failure"

    Agent->>SDK: Run exits (__exit__)
    SDK->>SDK: Capture ended_at<br/>Build AgentRunCreate payload

    SDK->>SDK: Validate metadata<br/>Check for forbidden keys
    SDK->>IngestAPI: POST /v1/runs<br/>Content-Type: application/json

    activate IngestAPI
    IngestAPI->>IngestAPI: Parse JSON body
    IngestAPI->>Pydantic: Validate with AgentRunCreate model

    activate Pydantic
    Pydantic->>Pydantic: Type checking<br/>Field validation
    Pydantic->>Pydantic: @field_validator("steps")<br/>Check sequence [0,1,2...]
    Pydantic->>Pydantic: @field_validator("metadata")<br/>Privacy check (no prompts)

    alt Validation Failed
        Pydantic-->>IngestAPI: raise ValueError
        IngestAPI-->>SDK: HTTP 400 Bad Request<br/>{"detail": "Validation error"}
        SDK-->>Agent: Log error
    else Validation Passed
        Pydantic-->>IngestAPI: Valid AgentRunCreate object
        deactivate Pydantic

        IngestAPI->>DB: SELECT * FROM agent_runs<br/>WHERE run_id = ?
        activate DB
        DB-->>IngestAPI: Query result

        alt Run Already Exists (Idempotency)
            IngestAPI->>IngestAPI: Fetch existing run
            IngestAPI-->>SDK: HTTP 200 OK<br/>AgentRunResponse (existing)
            SDK-->>Agent: Log: Duplicate run_id
        else New Run
            IngestAPI->>ORM: Create AgentRunDB object
            IngestAPI->>ORM: Create AgentStepDB objects (loop)
            IngestAPI->>ORM: Create AgentFailureDB object (if failure)

            IngestAPI->>DB: BEGIN TRANSACTION
            IngestAPI->>DB: INSERT INTO agent_runs
            IngestAPI->>DB: INSERT INTO agent_steps (batch)
            IngestAPI->>DB: INSERT INTO agent_failures (if present)

            alt DB Error
                DB-->>IngestAPI: IntegrityError / Exception
                IngestAPI->>DB: ROLLBACK
                IngestAPI-->>SDK: HTTP 409 Conflict or 500 Error
                SDK-->>Agent: Log error
            else Success
                IngestAPI->>DB: COMMIT
                DB-->>IngestAPI: Success
                deactivate DB

                IngestAPI->>ORM: db.refresh(run)
                IngestAPI->>IngestAPI: Increment metrics<br/>runs_ingested_total++

                IngestAPI->>Pydantic: Serialize to AgentRunResponse
                activate Pydantic
                Pydantic-->>IngestAPI: JSON response
                deactivate Pydantic

                IngestAPI-->>SDK: HTTP 201 Created<br/>AgentRunResponse
                deactivate IngestAPI
                SDK-->>Agent: Success
                deactivate SDK
            end
        end
    end
```

### Key Points

1. **Timing Capture**: SDK automatically captures timestamps via context managers
2. **Validation Layers**: SDK → Pydantic → Database constraints
3. **Idempotency**: Duplicate `run_id` returns existing run (HTTP 200)
4. **Transactional**: Single transaction for run + steps + failures
5. **Failure Handling**: Validation errors return HTTP 400, DB errors return HTTP 409/500

---

## Run Query Sequence

Sequence for querying runs with filters via the Query API.

```mermaid
sequenceDiagram
    participant UI as React UI
    participant ReactQuery as React Query
    participant Axios as Axios HTTP
    participant QueryAPI as Query API
    participant ORM as SQLAlchemy ORM
    participant DB as PostgreSQL

    UI->>ReactQuery: useQuery("runs", { agent_id, status, page })
    activate ReactQuery

    ReactQuery->>ReactQuery: Check cache<br/>Key: ["runs", filters]

    alt Data in Cache & Fresh
        ReactQuery-->>UI: Return cached data
    else Cache Miss or Stale
        ReactQuery->>Axios: axios.get("/v1/runs", { params })
        activate Axios

        Axios->>QueryAPI: GET /v1/runs?agent_id=X&status=Y&page=1&page_size=20
        activate QueryAPI

        QueryAPI->>ORM: Build SQLAlchemy query<br/>db.query(AgentRunDB)

        QueryAPI->>ORM: .filter(agent_id == X)
        QueryAPI->>ORM: .filter(status == Y)
        QueryAPI->>ORM: .order_by(desc(started_at))

        QueryAPI->>ORM: Calculate pagination<br/>offset = (page-1) * page_size
        QueryAPI->>ORM: .offset(offset).limit(page_size)

        QueryAPI->>DB: SELECT * FROM agent_runs<br/>WHERE agent_id=X AND status=Y<br/>ORDER BY started_at DESC<br/>LIMIT 20 OFFSET 0

        activate DB
        DB->>DB: Use indexes:<br/>- agent_id<br/>- status<br/>- started_at
        DB-->>QueryAPI: Return rows (List[AgentRunDB])
        deactivate DB

        QueryAPI->>ORM: Convert to Pydantic<br/>AgentRunResponse.model_validate()
        ORM-->>QueryAPI: List[AgentRunResponse]

        QueryAPI->>QueryAPI: Serialize to JSON
        QueryAPI-->>Axios: HTTP 200 OK<br/>Content-Type: application/json<br/>[{run1}, {run2}, ...]
        deactivate QueryAPI

        Axios-->>ReactQuery: Response data
        deactivate Axios

        ReactQuery->>ReactQuery: Update cache<br/>staleTime: 5 minutes
        ReactQuery-->>UI: Return fresh data
        deactivate ReactQuery

        UI->>UI: Render RunExplorer<br/>Display runs in table
    end
```

### Key Points

1. **Client Caching**: React Query caches for 5 minutes to reduce API calls
2. **Filtering**: Multiple filters can be combined (agent_id, status, environment, time range)
3. **Pagination**: Offset/limit pattern, page-based
4. **Indexing**: Uses database indexes for fast WHERE clauses
5. **Serialization**: ORM objects → Pydantic → JSON

---

## Stats Aggregation Sequence

Sequence for fetching aggregated statistics for the Dashboard.

```mermaid
sequenceDiagram
    participant Dashboard as Dashboard Page
    participant ReactQuery as React Query
    participant QueryAPI as Query API
    participant DB as PostgreSQL

    Dashboard->>ReactQuery: useQuery("stats", { agent_id, start_time })
    activate ReactQuery

    ReactQuery->>QueryAPI: GET /v1/stats?agent_id=X&start_time=Y
    activate QueryAPI

    QueryAPI->>QueryAPI: Build base query<br/>runs_query = db.query(AgentRunDB)
    QueryAPI->>QueryAPI: Apply filters<br/>.filter(agent_id == X)<br/>.filter(started_at >= Y)

    par Count Total Runs
        QueryAPI->>DB: SELECT COUNT(*) FROM agent_runs<br/>WHERE agent_id=X AND started_at>=Y
        activate DB
        DB-->>QueryAPI: total_runs = 100
        deactivate DB
    and Count Failures
        QueryAPI->>DB: SELECT COUNT(*) FROM agent_runs<br/>WHERE agent_id=X AND status='failure'
        activate DB
        DB-->>QueryAPI: total_failures = 25
        deactivate DB
    end

    QueryAPI->>QueryAPI: success_rate = (100-25)/100 * 100 = 75%

    QueryAPI->>DB: SELECT run_id FROM agent_runs<br/>WHERE agent_id=X (for subqueries)
    activate DB
    DB-->>QueryAPI: run_ids = [id1, id2, ...]
    deactivate DB

    par Average Latency
        QueryAPI->>DB: SELECT AVG(latency_ms) FROM agent_steps<br/>WHERE run_id IN (run_ids)
        activate DB
        DB-->>QueryAPI: avg_latency = 250.5
        deactivate DB
    and Failure Breakdown
        QueryAPI->>DB: SELECT failure_type, failure_code, COUNT(*)<br/>FROM agent_failures<br/>WHERE run_id IN (run_ids)<br/>GROUP BY failure_type, failure_code
        activate DB
        DB-->>QueryAPI: [<br/> ('tool','timeout',15),<br/> ('model','rate_limit',8)<br/>]
        deactivate DB
    and Step Type Breakdown
        QueryAPI->>DB: SELECT step_type, COUNT(*)<br/>FROM agent_steps<br/>WHERE run_id IN (run_ids)<br/>GROUP BY step_type
        activate DB
        DB-->>QueryAPI: [<br/> ('plan',100),<br/> ('tool',250),<br/> ('respond',100)<br/>]
        deactivate DB
    end

    QueryAPI->>QueryAPI: Build response object:<br/>{<br/> total_runs: 100,<br/> total_failures: 25,<br/> success_rate: 75.0,<br/> avg_latency_ms: 250.5,<br/> failure_breakdown: {...},<br/> step_type_breakdown: {...}<br/>}

    QueryAPI-->>ReactQuery: HTTP 200 OK<br/>JSON response
    deactivate QueryAPI

    ReactQuery->>ReactQuery: Cache for 5 minutes
    ReactQuery-->>Dashboard: Stats data
    deactivate ReactQuery

    Dashboard->>Dashboard: Render:<br/>- Success rate card<br/>- Failure breakdown chart<br/>- Step distribution chart<br/>- Recent activity
```

### Key Points

1. **Parallel Queries**: Multiple aggregations run in parallel for performance
2. **Subquery Pattern**: Get run_ids first, then aggregate related data
3. **GROUP BY**: Aggregates failures by type/code, steps by type
4. **Calculation**: Success rate calculated in Python (could be done in SQL)
5. **Caching**: Results cached for 5 minutes

---

## Run Detail Sequence

Sequence for fetching a single run with all steps and failures.

```mermaid
sequenceDiagram
    participant UI as RunDetail Page
    participant ReactQuery as React Query
    participant QueryAPI as Query API
    participant ORM as SQLAlchemy ORM
    participant DB as PostgreSQL

    UI->>ReactQuery: useQuery(["run", run_id])
    activate ReactQuery

    ReactQuery->>QueryAPI: GET /v1/runs/{run_id}
    activate QueryAPI

    QueryAPI->>ORM: db.query(AgentRunDB)<br/>.filter(run_id == ?)
    QueryAPI->>ORM: Eager load relationships:<br/>.options(joinedload(steps))<br/>.options(joinedload(failures))

    QueryAPI->>DB: SELECT * FROM agent_runs<br/>LEFT JOIN agent_steps ON ...<br/>LEFT JOIN agent_failures ON ...<br/>WHERE run_id = ?

    activate DB
    DB->>DB: Use primary key index<br/>on run_id
    DB-->>QueryAPI: Run with nested steps and failures
    deactivate DB

    alt Run Not Found
        QueryAPI-->>ReactQuery: HTTP 404 Not Found<br/>{"detail": "Run not found"}
        ReactQuery-->>UI: Error state
        UI->>UI: Display "Run not found"
    else Run Found
        QueryAPI->>ORM: Construct AgentRunDB object<br/>with steps[] and failures[]

        QueryAPI->>ORM: Convert to Pydantic<br/>AgentRunResponse.model_validate()
        activate ORM
        ORM->>ORM: Serialize run
        ORM->>ORM: Serialize nested steps<br/>(AgentStepResponse for each)
        ORM->>ORM: Serialize nested failures<br/>(AgentFailureResponse for each)
        ORM-->>QueryAPI: AgentRunResponse<br/>{<br/> run_id, agent_id, status,<br/> steps: [{seq,type,name,latency}],<br/> failures: [{type,code,message}]<br/>}
        deactivate ORM

        QueryAPI-->>ReactQuery: HTTP 200 OK<br/>Complete run with nested data
        deactivate QueryAPI

        ReactQuery->>ReactQuery: Cache response
        ReactQuery-->>UI: Run data
        deactivate ReactQuery

        UI->>UI: Render components:<br/>- Run metadata<br/>- TraceTimeline (steps)<br/>- FailureBreakdown (failures)
    end
```

### Key Points

1. **Eager Loading**: Single query fetches run + steps + failures (prevents N+1)
2. **Relationships**: SQLAlchemy `joinedload` loads related data
3. **Nested Serialization**: Pydantic serializes nested lists automatically
4. **Not Found Handling**: Returns HTTP 404 if run doesn't exist
5. **Rich Response**: Complete run data for detailed view

---

## Error Handling Sequences

Common error scenarios and their handling.

### Validation Error (HTTP 400)

```mermaid
sequenceDiagram
    participant SDK
    participant API
    participant Pydantic

    SDK->>API: POST /v1/runs (invalid data)
    API->>Pydantic: Validate AgentRunCreate

    Pydantic->>Pydantic: Check step sequence<br/>[0, 2, 3] ❌ Missing 1

    Pydantic-->>API: raise ValueError<br/>"Steps must have sequential seq values"

    API->>API: Catch validation error
    API-->>SDK: HTTP 400 Bad Request<br/>{<br/> "detail": "Steps must have sequential seq values"<br/>}

    SDK->>SDK: Log error
    SDK-->>SDK: Do not retry<br/>(client error)
```

### Database Constraint Error (HTTP 409)

```mermaid
sequenceDiagram
    participant SDK
    participant API
    participant DB

    SDK->>API: POST /v1/runs
    API->>DB: INSERT INTO agent_runs

    DB->>DB: Check constraints<br/>status IN ('success','failure','partial')

    DB-->>API: IntegrityError<br/>"violates check constraint"

    API->>DB: ROLLBACK
    API-->>SDK: HTTP 409 Conflict<br/>{<br/> "detail": "Data integrity violation"<br/>}

    SDK->>SDK: Log error
```

### Database Connection Error (HTTP 503)

```mermaid
sequenceDiagram
    participant UI
    participant API
    participant DB

    UI->>API: GET /health
    API->>DB: SELECT 1

    DB-->>API: Connection refused ❌

    API->>API: Catch exception
    API-->>UI: HTTP 503 Service Unavailable<br/>{<br/> "status": "unhealthy",<br/> "detail": "Database connection failed"<br/>}

    UI->>UI: Display error banner<br/>"Service unavailable"
```

---

## Performance Optimization Patterns

### Batch Insert Pattern (Ingest API)

```mermaid
sequenceDiagram
    participant API as Ingest API
    participant DB as PostgreSQL

    Note over API: Receive run with 10 steps

    API->>DB: BEGIN TRANSACTION
    API->>DB: INSERT INTO agent_runs (1 row)
    API->>DB: INSERT INTO agent_steps VALUES<br/>(step1), (step2), ..., (step10)<br/>Batch insert in single statement

    alt Success
        API->>DB: COMMIT
        Note over API,DB: Single round-trip for all steps
    else Error
        API->>DB: ROLLBACK
        Note over API,DB: All-or-nothing semantics
    end
```

### Pagination Pattern (Query API)

```mermaid
sequenceDiagram
    participant UI
    participant API
    participant DB

    UI->>API: GET /v1/runs?page=1&page_size=20
    API->>DB: SELECT * FROM agent_runs<br/>ORDER BY started_at DESC<br/>LIMIT 20 OFFSET 0

    DB-->>API: 20 rows (fast with index)
    API-->>UI: Page 1 data

    UI->>API: GET /v1/runs?page=2&page_size=20
    API->>DB: SELECT * FROM agent_runs<br/>ORDER BY started_at DESC<br/>LIMIT 20 OFFSET 20

    DB-->>API: 20 rows
    API-->>UI: Page 2 data

    Note over UI,DB: Only fetch what's needed,<br/>not all data at once
```

---

## Next Steps

- Review [Data Flow](./data-flow.md) for end-to-end flow context
- See [Failure Handling](./failure-handling.md) for failure capture sequences
- Check [Component Responsibilities](./component-responsibility.md) for layer boundaries
