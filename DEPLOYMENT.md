# Agent Observability Platform — Production Deployment Guide

This guide covers deploying the Agent Observability Platform to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Setup](#database-setup)
4. [Application Deployment](#application-deployment)
5. [Security Hardening](#security-hardening)
6. [Monitoring & Observability](#monitoring--observability)
7. [Scaling Considerations](#scaling-considerations)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.10+**
- **PostgreSQL 15+** (or managed database service)
- **Docker & Docker Compose** (recommended)
- **Domain name** with SSL certificate
- **Reverse proxy** (Nginx, Caddy, or cloud load balancer)

### Recommended

- **Cloud provider account** (AWS, GCP, Azure)
- **CI/CD pipeline** (GitHub Actions, GitLab CI)
- **Monitoring tools** (Prometheus, Grafana, Sentry)
- **Log aggregation** (ELK Stack, CloudWatch)

---

## Infrastructure Setup

### Option 1: Cloud Deployment (AWS Example)

#### 1.1 Database (RDS PostgreSQL)

```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier agent-observability-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password <SECURE_PASSWORD> \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name your-db-subnet \
  --backup-retention-period 7 \
  --multi-az \
  --storage-encrypted \
  --publicly-accessible false
```

#### 1.2 Application Servers (ECS or EC2)

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name agent-observability-cluster

# Create task definitions for ingest and query APIs
# (See ecs-task-definition.json)

# Deploy services
aws ecs create-service \
  --cluster agent-observability-cluster \
  --service-name ingest-api \
  --task-definition agent-obs-ingest:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

#### 1.3 Load Balancer

```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name agent-obs-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx \
  --scheme internet-facing

# Create target groups for ingest and query APIs
# Configure health checks
# Set up routing rules
```

### Option 2: Docker Compose Deployment

For smaller deployments or self-hosted environments:

```yaml
# production-docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agent_observability
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  ingest_api:
    build: .
    command: uvicorn backend.ingest_api:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5433/agent_observability
      LOG_LEVEL: INFO
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  query_api:
    build: .
    command: uvicorn backend.query_api:app --host 0.0.0.0 --port 8001 --workers 2
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5433/agent_observability
      LOG_LEVEL: INFO
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - ingest_api
      - query_api
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## Database Setup

### 1. Create Database

```bash
# Apply schema
psql -h <DB_HOST> -U postgres -d agent_observability < db/schema.sql

# Verify tables
psql -h <DB_HOST> -U postgres -d agent_observability -c "\dt"
```

### 2. Create Read-Only User (for Query API)

```sql
-- Create read-only role
CREATE ROLE query_api_readonly;
GRANT CONNECT ON DATABASE agent_observability TO query_api_readonly;
GRANT USAGE ON SCHEMA public TO query_api_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO query_api_readonly;

-- Create user
CREATE USER query_api WITH PASSWORD 'secure_password';
GRANT query_api_readonly TO query_api;
```

### 3. Database Optimization

```sql
-- Create additional indexes for production
CREATE INDEX CONCURRENTLY idx_runs_composite
  ON agent_runs(agent_id, started_at DESC);

CREATE INDEX CONCURRENTLY idx_failures_composite
  ON agent_failures(failure_type, failure_code);

-- Analyze tables
ANALYZE agent_runs;
ANALYZE agent_steps;
ANALYZE agent_failures;

-- Set up autovacuum
ALTER TABLE agent_runs SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE agent_steps SET (autovacuum_vacuum_scale_factor = 0.05);
```

---

## Application Deployment

### 1. Environment Configuration

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://postgres:PASSWORD@db-host:5433/agent_observability
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# API Configuration
INGEST_API_HOST=0.0.0.0
INGEST_API_PORT=8000
INGEST_API_WORKERS=4

QUERY_API_HOST=0.0.0.0
QUERY_API_PORT=8001
QUERY_API_WORKERS=2

# Authentication
API_KEY=your-secure-api-key-here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
PROMETHEUS_PORT=9090

# Environment
ENVIRONMENT=production
```

### 2. Build and Deploy

```bash
# Build Docker images
docker build -t agent-obs-ingest:1.0.0 .
docker build -t agent-obs-query:1.0.0 .

# Tag and push to registry
docker tag agent-obs-ingest:1.0.0 your-registry/agent-obs-ingest:1.0.0
docker push your-registry/agent-obs-ingest:1.0.0

# Deploy with docker-compose
docker-compose -f production-docker-compose.yml up -d

# Or deploy to Kubernetes (see k8s/ directory)
kubectl apply -f k8s/
```

### 3. Run Migrations

```bash
# Apply database schema
python -m alembic upgrade head

# Verify deployment
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

## Security Hardening

### 1. Network Security

```nginx
# nginx.conf - Rate limiting
http {
    limit_req_zone $binary_remote_addr zone=ingest:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=query:10m rate=50r/s;

    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        # Ingest API
        location /v1/runs {
            limit_req zone=ingest burst=20;
            proxy_pass http://ingest_api:8000;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Query API
        location /v1/ {
            limit_req zone=query burst=10;
            proxy_pass http://query_api:8001;
        }
    }
}
```

### 2. API Authentication

Update `backend/ingest_api.py`:

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/v1/runs", dependencies=[Depends(verify_api_key)])
async def ingest_run(...):
    ...
```

### 3. Database Security

```sql
-- Restrict network access
-- Use SSL connections only
ALTER SYSTEM SET ssl = on;

-- Set connection limits
ALTER USER postgres CONNECTION LIMIT 50;

-- Enable row-level security (if needed)
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
```

---

## Monitoring & Observability

### 1. Application Metrics

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
runs_ingested = Counter('runs_ingested_total', 'Total runs ingested')
ingest_latency = Histogram('ingest_latency_seconds', 'Ingest latency')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 2. Health Checks

```bash
# Kubernetes health checks
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 3. Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("run_ingested", run_id=run_id, agent_id=agent_id)
```

---

## Scaling Considerations

### Horizontal Scaling

- **Ingest API**: Stateless, can scale to N instances
- **Query API**: Stateless, can scale to N instances
- **Database**: Use read replicas for query scaling

### Performance Optimization

```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

### Caching (Future Enhancement)

```python
# Redis caching for frequently accessed runs
from redis import Redis

cache = Redis(host='localhost', port=6379)

@app.get("/v1/runs/{run_id}")
async def get_run(run_id: UUID):
    # Check cache first
    cached = cache.get(f"run:{run_id}")
    if cached:
        return json.loads(cached)

    # Fetch from DB and cache
    run = db.query(...).first()
    cache.setex(f"run:{run_id}", 3600, json.dumps(run))
    return run
```

---

## Troubleshooting

### High Latency

```bash
# Check database slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

# Check connection pool
SELECT count(*), state
FROM pg_stat_activity
GROUP BY state;
```

### Memory Issues

```bash
# Monitor container memory
docker stats

# Adjust worker counts
uvicorn backend.ingest_api:app --workers 2  # Reduce if OOM
```

### Database Connection Errors

```bash
# Check connection limits
SELECT * FROM pg_settings WHERE name = 'max_connections';

# Check active connections
SELECT count(*) FROM pg_stat_activity;
```

---

## Rollback Procedure

```bash
# Docker Compose
docker-compose down
docker-compose -f production-docker-compose.yml up -d <previous-version>

# Kubernetes
kubectl rollout undo deployment/ingest-api
kubectl rollout undo deployment/query-api

# Database (if needed)
alembic downgrade -1
```

---

## Checklist

Before going live:

- [ ] Database backups configured
- [ ] SSL certificates installed
- [ ] API authentication enabled
- [ ] Rate limiting configured
- [ ] Monitoring dashboards set up
- [ ] Alerts configured
- [ ] Load testing completed
- [ ] Disaster recovery plan documented
- [ ] Runbook created for on-call
- [ ] Security audit completed

---

For support, contact: [Add contact information]
