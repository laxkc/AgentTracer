# Deployment Documentation

This document describes the Docker-based deployment architecture for the AgentTracer Platform.

## Table of Contents
- [Docker Container Architecture](#docker-container-architecture)
- [Network Communication](#network-communication)
- [Health Check Flow](#health-check-flow)
- [Environment Configuration](#environment-configuration)
- [Scaling Strategy](#scaling-strategy)

---

## Docker Container Architecture

The platform runs as multiple Docker containers orchestrated via Docker Compose.

```mermaid
graph TB
    subgraph DockerHost["Docker Host"]
        subgraph Network["Docker Network: agent_observability_network"]
            subgraph Database["Database Container"]
                DB["postgres:15-alpine<br/>───────────────<br/>Container: agent_observability_db<br/>Internal Port: 5432<br/>External Port: 5433<br/>Volume: postgres_data<br/>Health: pg_isready"]
            end

            subgraph IngestService["Ingest API Container"]
                Ingest["Python 3.10-slim<br/>───────────────<br/>Container: agent_observability_ingest_api<br/>Port: 8000<br/>Command: uvicorn backend.ingest_api:app<br/>Depends: postgres healthy"]
            end

            subgraph QueryService["Query API Container"]
                Query["Python 3.10-slim<br/>───────────────<br/>Container: agent_observability_query_api<br/>Port: 8001<br/>Command: uvicorn backend.query_api:app<br/>Depends: postgres healthy"]
            end
        end

        subgraph Volumes["Docker Volumes"]
            PGData[(postgres_data<br/>Persisted DB data)]
        end
    end

    subgraph External["External Systems"]
        direction LR
        Agents[Agent Applications<br/>using Python SDK]
        UI[React UI<br/>development server<br/>:3000]
    end

    Agents -->|HTTP POST :8000| Ingest
    UI -->|HTTP GET :8001| Query

    Ingest -->|PostgreSQL| DB
    Query -->|PostgreSQL| DB

    DB -.->|Mount| PGData

    style DB fill:#336791,stroke:#2c5282,color:#fff
    style Ingest fill:#3b82f6,stroke:#2563eb,color:#fff
    style Query fill:#10b981,stroke:#059669,color:#fff
    style PGData fill:#f59e0b,stroke:#d97706,color:#fff
    style Agents fill:#a855f7,stroke:#7c3aed,color:#fff
    style UI fill:#ec4899,stroke:#db2777,color:#fff
```

### Container Details

| Container | Image | Port Mapping | Dependencies | Purpose |
|-----------|-------|--------------|--------------|---------|
| `agent_observability_db` | `postgres:15-alpine` | `5433:5432` | None | PostgreSQL database |
| `agent_observability_ingest_api` | Custom (Python 3.10) | `8000:8000` | postgres (healthy) | Write-only API |
| `agent_observability_query_api` | Custom (Python 3.10) | `8001:8001` | postgres (healthy) | Read-only API |

### Port Mapping Explanation

```
External    Container
  Port    →   Port     Description
────────────────────────────────────────
  5433   →   5432     PostgreSQL (host access)
  8000   →   8000     Ingest API
  8001   →   8001     Query API
  3000   →   80       UI (future Docker deployment)
```

**Important:** Internal container communication uses container names and internal ports:
- Ingest API connects to database at `postgres:5432` (not `localhost:5433`)
- Query API connects to database at `postgres:5432` (not `localhost:5433`)

---

## Network Communication

Detailed network flow between containers and external systems.

```mermaid
flowchart TB
    subgraph ExternalNet["External Network (Host)"]
        direction LR
        Agent[Agent Application<br/>localhost SDK]
        Browser[Web Browser]
    end

    subgraph DockerNet["Docker Bridge Network<br/>agent_observability_network"]
        direction TB

        IngestAPI["Ingest API Container<br/>───────────────<br/>Hostname: ingest_api<br/>Internal: ingest_api:8000<br/>External: localhost:8000"]

        QueryAPI["Query API Container<br/>───────────────<br/>Hostname: query_api<br/>Internal: query_api:8001<br/>External: localhost:8001"]

        PostgreSQL["PostgreSQL Container<br/>───────────────<br/>Hostname: postgres<br/>Internal: postgres:5432<br/>External: localhost:5433"]
    end

    Agent -->|"POST http://localhost:8000/v1/runs"| Port8000[Port 8000<br/>Docker Port Mapping]
    Browser -->|"GET http://localhost:8001/v1/runs"| Port8001[Port 8001<br/>Docker Port Mapping]

    Port8000 -.->|Forward to container| IngestAPI
    Port8001 -.->|Forward to container| QueryAPI

    IngestAPI -->|"postgresql://postgres:postgres@postgres:5432/agent_observability"| PostgreSQL
    QueryAPI -->|"postgresql://postgres:postgres@postgres:5432/agent_observability"| PostgreSQL

    style ExternalNet fill:#f3f4f6,stroke:#9ca3af
    style DockerNet fill:#dbeafe,stroke:#3b82f6
    style PostgreSQL fill:#336791,stroke:#2c5282,color:#fff
    style IngestAPI fill:#3b82f6,stroke:#2563eb,color:#fff
    style QueryAPI fill:#10b981,stroke:#059669,color:#fff
```

### Network Security

```mermaid
graph LR
    subgraph Public["Public Access"]
        ExtAgent[External Agents]
        ExtUI[External UI Users]
    end

    subgraph DockerNetwork["Docker Internal Network"]
        IngestAPI[Ingest API<br/>Exposed :8000]
        QueryAPI[Query API<br/>Exposed :8001]
        Database[PostgreSQL<br/>Not Exposed]
    end

    ExtAgent -->|✅ Public Access| IngestAPI
    ExtUI -->|✅ Public Access| QueryAPI

    IngestAPI -->|✅ Internal Only| Database
    QueryAPI -->|✅ Internal Only| Database

    ExtAgent -.->|❌ No Direct Access| Database
    ExtUI -.->|❌ No Direct Access| Database

    style Public fill:#fee2e2,stroke:#dc2626
    style DockerNetwork fill:#dcfce7,stroke:#16a34a
    style Database fill:#fef3c7,stroke:#ca8a04
```

**Security Boundaries:**
1. **Database**: Only accessible from within Docker network (not exposed to host beyond port mapping for tools)
2. **APIs**: Exposed to host network for external access
3. **Future**: Add HTTPS termination with reverse proxy (nginx)

---

## Health Check Flow

Container startup sequence with health checks and dependencies.

```mermaid
flowchart TD
    Start([docker compose up]) --> CheckImages{Images exist?}

    CheckImages -->|No| BuildImages[docker compose build]
    CheckImages -->|Yes| StartDB

    BuildImages --> BuildIngest[Build ingest_api image<br/>FROM python:3.10-slim]
    BuildImages --> BuildQuery[Build query_api image<br/>FROM python:3.10-slim]

    BuildIngest --> StartDB
    BuildQuery --> StartDB

    StartDB[Start postgres container] --> InitDB[Run schema.sql<br/>via docker-entrypoint-initdb.d]

    InitDB --> HealthLoop{Health Check Loop}

    HealthLoop -->|Every 10s| RunCheck[pg_isready -U postgres]
    RunCheck --> CheckResult{Result?}

    CheckResult -->|Fail| Retry{Retries < 5?}
    Retry -->|Yes| Wait[Wait 10s]
    Wait --> RunCheck
    Retry -->|No| Unhealthy[Mark unhealthy<br/>❌ Fail startup]

    CheckResult -->|Success| Healthy[Mark postgres healthy ✅]

    Healthy --> StartIngest[Start ingest_api container<br/>Wait: postgres healthy]
    Healthy --> StartQuery[Start query_api container<br/>Wait: postgres healthy]

    StartIngest --> IngestInit[Run database migrations<br/>Base.metadata.create_all]
    StartQuery --> QueryReady[Query API ready]

    IngestInit --> IngestReady[Ingest API ready]

    IngestReady --> AllRunning{All containers<br/>running?}
    QueryReady --> AllRunning

    AllRunning -->|Yes| Success([✅ System Ready<br/>Accept Requests])
    AllRunning -->|No| Failure([❌ Startup Failed<br/>Check logs])

    style Start fill:#10b981,stroke:#059669,color:#fff
    style Healthy fill:#10b981,stroke:#059669,color:#fff
    style Success fill:#10b981,stroke:#059669,color:#fff
    style Unhealthy fill:#ef4444,stroke:#dc2626,color:#fff
    style Failure fill:#ef4444,stroke:#dc2626,color:#fff
```

### Health Check Configuration

**PostgreSQL Health Check:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**API Health Endpoints:**
```python
# Both APIs expose health endpoints
GET /health

# Response when healthy:
{
  "status": "healthy",
  "service": "ingest-api" | "query-api",
  "version": "0.1.0"
}

# Response when unhealthy (database connection failed):
{
  "detail": "Database connection failed: ..."
}
HTTP 503 Service Unavailable
```

**Monitoring Health:**
```bash
# Check all container statuses
docker compose ps

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health

# View container logs
docker compose logs postgres
docker compose logs ingest_api
docker compose logs query_api
```

---

## Environment Configuration

Environment variables and configuration management.

```mermaid
flowchart LR
    subgraph ConfigSources["Configuration Sources"]
        EnvFile[.env file<br/>optional]
        ComposeFile[docker-compose.yml<br/>environment section]
        Defaults[Code defaults<br/>os.getenv]
    end

    subgraph Containers["Containers"]
        direction TB

        DB["PostgreSQL<br/>───────────────<br/>POSTGRES_DB=agent_observability<br/>POSTGRES_USER=postgres<br/>POSTGRES_PASSWORD=postgres"]

        Ingest["Ingest API<br/>───────────────<br/>DATABASE_URL=postgresql://...<br/>optional: LOG_LEVEL<br/>optional: API_KEY"]

        Query["Query API<br/>───────────────<br/>DATABASE_URL=postgresql://...<br/>optional: LOG_LEVEL"]
    end

    EnvFile -.->|Override| ComposeFile
    ComposeFile -->|Inject| DB
    ComposeFile -->|Inject| Ingest
    ComposeFile -->|Inject| Query

    Defaults -.->|Fallback if not set| Ingest
    Defaults -.->|Fallback if not set| Query

    style EnvFile fill:#fef3c7,stroke:#ca8a04
    style ComposeFile fill:#dbeafe,stroke:#3b82f6
    style Defaults fill:#e0e7ff,stroke:#6366f1
```

### Key Environment Variables

**PostgreSQL Container:**
```yaml
environment:
  POSTGRES_DB: agent_observability
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres  # Change in production!
```

**Ingest API Container:**
```yaml
environment:
  DATABASE_URL: postgresql://postgres:postgres@postgres:5432/agent_observability
  # Optional:
  LOG_LEVEL: INFO
  API_KEY: your-secret-key  # For authentication (future)
```

**Query API Container:**
```yaml
environment:
  DATABASE_URL: postgresql://postgres:postgres@postgres:5432/agent_observability
  # Optional:
  LOG_LEVEL: INFO
```

### Code-Level Defaults

```python
# backend/ingest_api.py
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/agent_observability"
)
```

**Note:** Fallback assumes localhost for local development without Docker.

---

## Scaling Strategy

Future horizontal scaling architecture.

```mermaid
graph TB
    subgraph LoadBalancing["Load Balancing Layer"]
        LB[Load Balancer<br/>Nginx/HAProxy]
    end

    subgraph IngestCluster["Ingest API Cluster"]
        I1[Ingest API 1]
        I2[Ingest API 2]
        I3[Ingest API N]
    end

    subgraph QueryCluster["Query API Cluster"]
        Q1[Query API 1]
        Q2[Query API 2]
        Q3[Query API N]
    end

    subgraph DatabaseLayer["Database Layer"]
        Primary[(PostgreSQL<br/>Primary<br/>Read+Write)]
        Replica1[(PostgreSQL<br/>Replica 1<br/>Read-only)]
        Replica2[(PostgreSQL<br/>Replica 2<br/>Read-only)]
    end

    subgraph Monitoring["Monitoring & Observability"]
        Prometheus[Prometheus<br/>Metrics Collection]
        Grafana[Grafana<br/>Dashboards]
        Logs[Centralized Logging<br/>ELK Stack]
    end

    LB -->|Write Traffic| IngestCluster
    LB -->|Read Traffic| QueryCluster

    I1 -->|All Writes| Primary
    I2 -->|All Writes| Primary
    I3 -->|All Writes| Primary

    Q1 -->|Load Balanced| Replica1
    Q1 -->|Load Balanced| Replica2
    Q2 -->|Load Balanced| Replica1
    Q2 -->|Load Balanced| Replica2
    Q3 -->|Load Balanced| Replica1
    Q3 -->|Load Balanced| Replica2

    Primary -.->|Streaming Replication| Replica1
    Primary -.->|Streaming Replication| Replica2

    IngestCluster -.->|Export Metrics| Prometheus
    QueryCluster -.->|Export Metrics| Prometheus
    DatabaseLayer -.->|Export Metrics| Prometheus

    Prometheus -->|Visualize| Grafana

    IngestCluster -.->|Ship Logs| Logs
    QueryCluster -.->|Ship Logs| Logs

    style LB fill:#64748b,stroke:#475569,color:#fff
    style Primary fill:#ef4444,stroke:#dc2626,color:#fff
    style Replica1 fill:#10b981,stroke:#059669,color:#fff
    style Replica2 fill:#10b981,stroke:#059669,color:#fff
    style Prometheus fill:#e74c3c,stroke:#c0392b,color:#fff
    style Grafana fill:#f39c12,stroke:#d68910,color:#fff
```

### Scaling Phases

**Phase 1 (Current):**
- Single instance of each service
- Single PostgreSQL database
- Docker Compose orchestration

**Phase 2 (Horizontal Scaling):**
- Multiple Ingest API instances behind load balancer
- Multiple Query API instances behind load balancer
- PostgreSQL read replicas for Query API
- Redis for caching (optional)

**Phase 3 (Full Production):**
- Kubernetes orchestration
- Auto-scaling based on metrics
- Multi-region deployment
- Distributed tracing
- Advanced monitoring

### Docker Compose Scaling

```bash
# Scale ingest API to 3 instances (Phase 2)
docker compose up -d --scale ingest_api=3

# Scale query API to 3 instances
docker compose up -d --scale query_api=3

# Note: Requires load balancer configuration
# and removal of fixed port mapping in docker-compose.yml
```

---

## Deployment Commands

### Development Deployment

```bash
# Start all services
docker compose up -d

# Build and start (force rebuild)
docker compose up -d --build

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

### Production Deployment

```bash
# Use production compose file (if separate)
docker compose -f docker-compose.prod.yml up -d

# Pull latest images (if using registry)
docker compose pull

# Restart specific service
docker compose restart ingest_api

# View resource usage
docker stats
```

### Database Management

```bash
# Access PostgreSQL shell
docker compose exec postgres psql -U postgres -d agent_observability

# Backup database
docker compose exec postgres pg_dump -U postgres agent_observability > backup.sql

# Restore database
docker compose exec -T postgres psql -U postgres agent_observability < backup.sql

# View database logs
docker compose logs postgres
```

---

## Troubleshooting

### Common Issues

**1. Database Connection Refused**
```bash
# Check postgres is healthy
docker compose ps

# If not healthy, check logs
docker compose logs postgres

# Ensure APIs use correct DATABASE_URL
# Should be: postgres:5432 (not localhost:5433)
```

**2. Port Already in Use**
```bash
# Find process using port
lsof -i :8000
lsof -i :8001
lsof -i :5433

# Kill process or change port in docker-compose.yml
```

**3. Container Won't Start**
```bash
# View detailed logs
docker compose logs ingest_api

# Rebuild image
docker compose build ingest_api

# Remove old containers and restart
docker compose down
docker compose up -d
```

**4. Schema Not Applied**
```bash
# Recreate database with schema
docker compose down -v  # ⚠️ Deletes data
docker compose up -d

# Or manually run schema
docker compose exec -T postgres psql -U postgres agent_observability < db/schema.sql
```

---

## Next Steps

- Review [Architecture](./architecture.md) for system overview
- See [Component Responsibilities](./component-responsibility.md) for container roles
- Check [Data Flow](./data-flow.md) for network communication details
