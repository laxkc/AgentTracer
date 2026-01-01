# System Architecture

This document describes the architecture of the Agent Observability Platform, showing how components interact and responsibilities are distributed.

## Table of Contents
- [Component Architecture](#component-architecture)
- [Layer Architecture](#layer-architecture)
- [Technology Stack](#technology-stack)
- [Component Details](#component-details)

---

## Component Architecture

The system follows a microservices-inspired architecture with clear separation between read and write operations.

```mermaid
graph TB
    subgraph External["External Systems"]
        Agent1[Agent Application 1]
        Agent2[Agent Application 2]
        AgentN[Agent Application N]
    end

    subgraph SDK["SDK Layer"]
        SDK1[Python SDK]
        SDK2[Python SDK]
        SDKN[Python SDK]
    end

    subgraph Backend["Backend Services (Docker)"]
        direction LR
        IngestAPI["Ingest API<br/>:8000<br/>(Write-Only)"]
        QueryAPI["Query API<br/>:8001<br/>(Read-Only)"]

        subgraph Database["Data Layer"]
            DB[(PostgreSQL<br/>:5433→5432)]
        end
    end

    subgraph Frontend["Frontend (Docker)"]
        UI["React UI<br/>:3000"]
    end

    Agent1 -.->|embedded| SDK1
    Agent2 -.->|embedded| SDK2
    AgentN -.->|embedded| SDKN

    SDK1 -->|HTTP POST<br/>/v1/runs| IngestAPI
    SDK2 -->|HTTP POST<br/>/v1/runs| IngestAPI
    SDKN -->|HTTP POST<br/>/v1/runs| IngestAPI

    IngestAPI -->|SQL Write| DB
    DB -->|SQL Read| QueryAPI

    QueryAPI -->|HTTP GET<br/>/v1/runs<br/>/v1/stats| UI

    style IngestAPI fill:#3b82f6,stroke:#2563eb,color:#fff
    style QueryAPI fill:#10b981,stroke:#059669,color:#fff
    style DB fill:#f59e0b,stroke:#d97706,color:#fff
    style UI fill:#ec4899,stroke:#db2777,color:#fff
    style SDK1 fill:#a855f7,stroke:#7c3aed,color:#fff
    style SDK2 fill:#a855f7,stroke:#7c3aed,color:#fff
    style SDKN fill:#a855f7,stroke:#7c3aed,color:#fff
```

### Key Design Decisions

1. **Read/Write Separation**: Ingest and Query APIs are separate services for scalability and security
2. **Stateless APIs**: Both APIs are stateless, allowing horizontal scaling
3. **Embedded SDK**: SDK runs within agent process, no separate service needed
4. **Single Database**: PostgreSQL handles both writes and reads (Phase 1 simplicity)

---

## Layer Architecture

The system is organized into distinct layers with clear responsibilities and boundaries.

```mermaid
graph TB
    subgraph Presentation["Presentation Layer"]
        direction LR
        Dashboard[Dashboard]
        RunExplorer[Run Explorer]
        RunDetail[Run Detail]
        Timeline[Trace Timeline]
        Failures[Failure Breakdown]
    end

    subgraph API["API Layer (CQRS Pattern)"]
        direction LR
        subgraph Write["Write Side"]
            IngestEndpoint[POST /v1/runs]
            IngestValidation[Pydantic Validation]
        end
        subgraph Read["Read Side"]
            QueryEndpoints[GET /v1/runs<br/>GET /v1/runs/:id<br/>GET /v1/stats]
            QueryFiltering[Filtering & Pagination]
        end
    end

    subgraph Data["Data Layer"]
        direction TB
        subgraph ORM["ORM Models"]
            RunDB[AgentRunDB]
            StepDB[AgentStepDB]
            FailureDB[AgentFailureDB]
        end
        subgraph Validation["Validation Models"]
            RunCreate[AgentRunCreate]
            RunResponse[AgentRunResponse]
        end
        subgraph Storage["Storage"]
            Tables[(agent_runs<br/>agent_steps<br/>agent_failures)]
        end
    end

    subgraph Instrumentation["Instrumentation Layer"]
        direction LR
        Tracer[AgentTracer]
        RunCtx[RunContext]
        StepCtx[StepContext]
    end

    Presentation -->|HTTP GET| Read
    Instrumentation -->|HTTP POST| Write

    Write -->|Validate & Save| ORM
    Read -->|Query & Serialize| ORM

    ORM -->|SQLAlchemy| Tables
    Validation -.->|Pydantic Models| ORM

    style Presentation fill:#ec4899,stroke:#db2777,color:#fff
    style Write fill:#3b82f6,stroke:#2563eb,color:#fff
    style Read fill:#10b981,stroke:#059669,color:#fff
    style ORM fill:#f59e0b,stroke:#d97706,color:#fff
    style Validation fill:#f59e0b,stroke:#d97706,color:#fff
    style Storage fill:#f59e0b,stroke:#d97706,color:#fff
    style Instrumentation fill:#a855f7,stroke:#7c3aed,color:#fff
```

### Layer Responsibilities

| Layer | Responsibilities | Technology |
|-------|-----------------|------------|
| **Presentation** | User interaction, visualization, client-side filtering | React + TypeScript |
| **API (Write)** | Validation, idempotency, privacy enforcement, writes | FastAPI + Pydantic |
| **API (Read)** | Querying, filtering, pagination, aggregation, reads | FastAPI + SQLAlchemy |
| **Data (ORM)** | Object-relational mapping, relationships, constraints | SQLAlchemy |
| **Data (Validation)** | Input validation, output serialization, type safety | Pydantic |
| **Data (Storage)** | Persistence, indexing, transactions, constraints | PostgreSQL 15 |
| **Instrumentation** | Timing capture, context management, privacy filtering | Python SDK |

---

## Technology Stack

Detailed mapping of technologies to architectural components.

```mermaid
graph LR
    subgraph Frontend["Frontend Stack"]
        React["React 18.2<br/>(UI Framework)"]
        TS["TypeScript 5.3<br/>(Type Safety)"]
        Vite["Vite 5.0<br/>(Build Tool)"]
        Tailwind["Tailwind CSS 3.3<br/>(Styling)"]
        ReactRouter["React Router 6<br/>(Routing)"]
        TanStack["TanStack Query 5<br/>(Data Fetching)"]
    end

    subgraph Backend["Backend Stack"]
        FastAPI["FastAPI 0.104<br/>(Web Framework)"]
        Python["Python 3.10<br/>(Runtime)"]
        SQLAlchemy["SQLAlchemy 2.0<br/>(ORM)"]
        Pydantic["Pydantic 2.5<br/>(Validation)"]
        Uvicorn["Uvicorn<br/>(ASGI Server)"]
    end

    subgraph Database["Database Stack"]
        PostgreSQL["PostgreSQL 15<br/>(RDBMS)"]
        Indexes["B-Tree Indexes<br/>(Performance)"]
        Constraints["CHECK Constraints<br/>(Data Integrity)"]
    end

    subgraph SDK["SDK Stack"]
        HTTPX["httpx<br/>(HTTP Client)"]
        ContextMgr["Context Managers<br/>(Auto-timing)"]
        AsyncIO["asyncio<br/>(Async I/O)"]
    end

    subgraph Infrastructure["Infrastructure Stack"]
        Docker["Docker 24+<br/>(Containers)"]
        Compose["Docker Compose<br/>(Orchestration)"]
        Alpine["Alpine Linux<br/>(Base Image)"]
    end

    Frontend -.->|HTTP| Backend
    Backend -.->|SQL| Database
    SDK -.->|HTTP| Backend

    style React fill:#61dafb,color:#000
    style FastAPI fill:#009688,color:#fff
    style PostgreSQL fill:#336791,color:#fff
    style Docker fill:#2496ed,color:#fff
```

### Technology Choices Rationale

**Frontend:**
- **React 18.2**: Industry standard, excellent ecosystem, concurrent features
- **TypeScript**: Type safety prevents runtime errors, better IDE support
- **Vite**: Fast HMR, modern build tool, optimized for development
- **Tailwind CSS**: Utility-first, rapid prototyping, small bundle size

**Backend:**
- **FastAPI**: High performance, automatic OpenAPI docs, async support
- **Pydantic**: Runtime validation, type coercion, serialization
- **SQLAlchemy 2.0**: Mature ORM, excellent PostgreSQL support
- **Python 3.10**: Modern Python features, type hints, pattern matching

**Database:**
- **PostgreSQL 15**: ACID compliance, JSON support, powerful indexing
- **Alpine Linux**: Minimal attack surface, small image size

**SDK:**
- **httpx**: Modern HTTP client, async support, HTTP/2
- **Context Managers**: Pythonic, automatic resource cleanup

---

## Component Details

### 1. Python SDK (AgentTracer)

**Location:** `sdk/agenttrace.py`

**Purpose:** Embedded library for capturing agent telemetry from within the agent process.

**Key Classes:**
- `AgentTracer`: Main entrypoint, configures connection to Ingest API
- `RunContext`: Manages a single agent run, tracks steps and failures
- `StepContext`: Captures timing for individual steps

**Responsibilities:**
- Automatic step timing via context managers
- Privacy enforcement (metadata validation)
- Fail-safe operation (never crashes agent)
- Async batched delivery to Ingest API

**Example:**
```python
tracer = AgentTracer(
    agent_id="my_agent",
    agent_version="1.0.0",
    api_url="http://localhost:8000"
)

with tracer.start_run() as run:
    with run.step("plan", "analyze_query"):
        # Agent logic here
        pass
```

---

### 2. Ingest API (Write-Only)

**Location:** `backend/ingest_api.py`

**Port:** 8000

**Purpose:** Write-only API for ingesting agent telemetry with strict validation.

**Key Endpoints:**
- `POST /v1/runs`: Ingest complete run with steps and failures
- `GET /health`: Health check
- `GET /metrics`: Internal metrics (Phase 1: simple counters)

**Responsibilities:**
- Schema validation (Pydantic)
- Idempotency via `run_id` (duplicate detection)
- Privacy enforcement (reject sensitive data)
- Transactional writes (atomicity)
- Fast writes (<200ms p99 target)

**Validation Layers:**
1. Pydantic schema validation
2. Privacy validators (no prompts/responses)
3. Business rules (step sequencing, failure requirements)
4. Database constraints (foreign keys, checks)

---

### 3. Query API (Read-Only)

**Location:** `backend/query_api.py`

**Port:** 8001

**Purpose:** Read-only API for querying runs with filtering and aggregation.

**Key Endpoints:**
- `GET /v1/runs`: List runs with filters and pagination
- `GET /v1/runs/{run_id}`: Get specific run with steps/failures
- `GET /v1/runs/{run_id}/steps`: Get ordered steps for a run
- `GET /v1/runs/{run_id}/failures`: Get failures for a run
- `GET /v1/stats`: Aggregated statistics
- `GET /health`: Health check

**Responsibilities:**
- Efficient queries with filtering
- Pagination support
- Aggregation for statistics
- No mutations (read-only guarantee)
- Response serialization

**Performance Features:**
- Indexed queries (agent_id, status, environment, timestamps)
- Pagination to limit data transfer
- Eager loading for relationships (steps, failures)

---

### 4. Database (PostgreSQL)

**Location:** Docker container `agent_observability_db`

**Port:** 5433→5432

**Purpose:** Persistent storage with relational integrity.

**Schema:**
- `agent_runs`: Run metadata (agent_id, version, status, timestamps)
- `agent_steps`: Ordered steps (seq, type, latency, metadata)
- `agent_failures`: Semantic failures (type, code, message)

**Key Features:**
- Foreign keys with cascade delete
- CHECK constraints for data integrity
- Unique constraints (run_id, step sequence)
- B-Tree indexes for common queries
- JSONB for safe metadata storage

**Indexes:**
- `agent_runs`: agent_id, status, environment, started_at
- `agent_steps`: run_id, step_type, started_at
- `agent_failures`: run_id, failure_type

---

### 5. React UI

**Location:** `ui/` directory

**Port:** 3000

**Purpose:** User interface for visualizing agent runs and failures.

**Key Pages:**
- **Dashboard**: Overview statistics, recent activity
- **Run Explorer**: Searchable/filterable run list
- **Run Detail**: Individual run with timeline and failures

**Key Components:**
- `TraceTimeline`: Visual step timeline with retry detection
- `FailureBreakdown`: Semantic failure classification display
- `RunExplorer`: Filterable run list with pagination

**Data Flow:**
- React Query for data fetching and caching
- Axios for HTTP client
- 5-minute stale time for cache optimization

---

## Scalability Considerations

### Horizontal Scaling (Future)

```mermaid
graph TB
    LB[Load Balancer]

    subgraph Ingest["Ingest API (Scaled)"]
        I1[Ingest API 1]
        I2[Ingest API 2]
        IN[Ingest API N]
    end

    subgraph Query["Query API (Scaled)"]
        Q1[Query API 1]
        Q2[Query API 2]
        QN[Query API N]
    end

    subgraph DB["Database (Read Replicas)"]
        Primary[(Primary<br/>Write)]
        Replica1[(Replica 1<br/>Read)]
        Replica2[(Replica 2<br/>Read)]
    end

    LB -->|Write Requests| Ingest
    LB -->|Read Requests| Query

    Ingest -->|All Writes| Primary
    Query -->|Load Balanced Reads| Replica1
    Query -->|Load Balanced Reads| Replica2

    Primary -.->|Replication| Replica1
    Primary -.->|Replication| Replica2

    style Primary fill:#ef4444,stroke:#dc2626,color:#fff
    style Replica1 fill:#10b981,stroke:#059669,color:#fff
    style Replica2 fill:#10b981,stroke:#059669,color:#fff
```

**Phase 1:** Single instance of each service
**Phase 2+:** Horizontal scaling with load balancing

---

## Security Boundaries

```mermaid
graph TB
    subgraph Public["Public Network"]
        Agents[Agent Applications]
        Users[UI Users]
    end

    subgraph DMZ["DMZ (Docker Network)"]
        IngestAPI[Ingest API<br/>Port 8000]
        QueryAPI[Query API<br/>Port 8001]
        UI[React UI<br/>Port 3000]
    end

    subgraph Private["Private Network"]
        DB[(Database<br/>Internal Only)]
    end

    Agents -->|HTTPS| IngestAPI
    Users -->|HTTPS| UI
    UI -->|HTTP| QueryAPI

    IngestAPI -->|PostgreSQL<br/>Internal| DB
    QueryAPI -->|PostgreSQL<br/>Internal| DB

    style Public fill:#ef4444,stroke:#dc2626,color:#fff
    style DMZ fill:#f59e0b,stroke:#d97706,color:#fff
    style Private fill:#10b981,stroke:#059669,color:#fff
```

**Security Layers:**
1. **Public**: Agent SDK and UI users (HTTPS in production)
2. **DMZ**: API and UI containers (Docker network isolation)
3. **Private**: Database (not exposed to public network)

---

## Next Steps

- Review [Data Flow](./data-flow.md) to understand how telemetry moves through the system
- See [Component Responsibilities](./component-responsibility.md) for detailed separation of concerns
- Check [Deployment](./deployment.md) for Docker architecture details
