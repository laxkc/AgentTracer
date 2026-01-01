\[FEATURE\] Agent Observability Platform — Phase 1 (MVP)
========================================================

1\. Current Context
-------------------

### 1.1 System Context

*   AI agents are deployed in production using LLMs + tools + orchestration frameworks.
    
*   Current observability relies on:
    
    *   application logs
        
    *   infra metrics
        
    *   generic distributed tracing
        
*   These tools **do not explain agent decisions, semantic failures, or step-level behavior**.
    

### 1.2 Existing Architecture (Before This Change)

*   Agent execution is opaque:
    
    *   reasoning is not visible
        
    *   tool failures are indistinguishable from infra failures
        
    *   retries and decision paths are not reconstructable
        
*   Debugging relies on:
    
    *   ad-hoc logs
        
    *   reproducing issues locally
        
    *   guesswork
        

### 1.3 Pain Points

*   Cannot answer **“why did the agent fail?”**
    
*   Cannot attribute **latency to agent steps**
    
*   Cannot compare **agent behavior across versions**
    
*   Cannot safely store traces due to privacy concerns
    

2\. Problem Statement
---------------------

> Build a Phase-1 Agent Observability system that makes agent behavior **visible, debuggable, and measurable** in production, without storing sensitive data.

This system must allow engineers to:

1.  Reconstruct a single agent run
    
2.  Identify slow or failing steps
    
3.  Classify failures semantically (tool / model / retrieval / orchestration)
    

3\. Requirements
----------------

### 3.1 Functional Requirements (Phase-1)

**Must Have**

*   Capture **agent runs** with ordered steps
    
*   Capture **step-level latency**
    
*   Capture **tool call metadata (safe only)**
    
*   Capture **semantic failure classification**
    
*   Query runs by:
    
    *   agent\_id
        
    *   agent\_version
        
    *   status
        
    *   time range
        
*   UI to visualize:
    
    *   run list
        
    *   step timeline
        
    *   failure breakdown
        
    *   step latency stats
        

**Explicitly Out of Scope (Phase-1)**

*   Raw prompt / response storage
    
*   Chain-of-thought storage
    
*   Automatic evaluation scoring
    
*   Replay / simulation
    
*   Hosted SaaS / multi-region
    

### 3.2 Non-Functional Requirements

#### Performance

*   SDK overhead per step < **2% runtime**
    
*   Ingest API p99 latency < **200ms**
    

#### Scalability

*   Handle bursty telemetry (many small writes)
    
*   Support thousands of runs/day (Phase-1 scale)
    

#### Reliability

*   At-least-once delivery from SDK
    
*   Idempotent ingest via run\_id
    

#### Observability (of the observability system)

*   API request latency
    
*   Ingest error rate
    
*   Dropped telemetry count
    

#### Security & Privacy

*   No raw prompts or responses
    
*   Metadata allow-list only
    
*   API key–based authentication
    

4\. Design Principles
---------------------

1.  **Decision-centric observability**Observe _what the agent did_, not just what code executed.
    
2.  **Privacy-by-default**Unsafe data is never collected in Phase-1.
    
3.  **Opinionated, minimal MVP**Fewer concepts, fewer schemas, fewer endpoints.
    
4.  **Extensible foundation**Phase-2 features must build on Phase-1 data without migration pain.
    

5\. Design Decisions
--------------------

### 5.1 Trace Model: Agent-Native Traces

**Decision:** Use an AgentRun → AgentStep\[\] → Failure model**Why:**

*   Mirrors agent control flow
    
*   Easier to reason than raw logs
    
*   Enables timeline visualization
    
*   Supports semantic failure attribution
    

**Alternatives Considered:**

*   Plain logs (rejected: unstructured, non-queryable)
    
*   Generic OTel spans only (rejected: no semantic meaning)
    

### 5.2 Failure Classification

**Decision:** Use (failure\_type, failure\_code) taxonomy**Why:**

*   Distinguishes semantic failures from infra failures
    
*   Enables aggregation and prioritization
    
*   Keeps Phase-1 simple
    

**Trade-offs:**

*   Requires SDK discipline
    
*   Some failures may be misclassified initially
    

### 5.3 Retry Modeling

**Decision:** Each retry is a **separate step span****Why:**

*   Enables accurate latency attribution
    
*   Makes retries visible in UI
    
*   Prevents hidden performance regressions
    

### 5.4 Storage Choice

**Decision:** PostgreSQL for Phase-1**Why:**

*   Fast to ship
    
*   Strong consistency
    
*   Good enough for MVP scale
    

**Future Path:**

*   ClickHouse / columnar DB for Phase-2+
    

6\. Technical Design
--------------------

### 6.1 Core Components

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   class AgentTracer:      """Client-side SDK entrypoint for capturing agent runs."""  class RunContext:      """Represents a single agent run."""  class StepContext:      """Represents a single step span with timing and metadata."""   `

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   class IngestAPI:      """Receives validated agent traces and persists them."""  class QueryAPI:      """Serves runs, traces, and aggregated stats to UI."""   `

### 6.2 Data Models (Conceptual)

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   class AgentRun:      run_id: UUID      agent_id: str      agent_version: str      environment: str      status: str      started_at: datetime      ended_at: datetime   `

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   class AgentStep:      step_id: UUID      run_id: UUID      seq: int      step_type: str      name: str      latency_ms: int      metadata: dict   `

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   class AgentFailure:      run_id: UUID      step_id: Optional[UUID]      failure_type: str      failure_code: str      message: str   `

### 6.3 Integration Points

*   **Agent SDK → Ingest API**
    
    *   HTTPS JSON
        
    *   Batched async delivery
        
*   **UI → Query API**
    
    *   Read-only queries
        
*   **No direct DB access from UI**
    

### 6.4 File Changes (Phase-1)

**New**

*   sdk/agenttrace.py
    
*   backend/ingest\_api.py
    
*   backend/query\_api.py
    
*   db/schema.sql
    
*   ui/RunExplorer.tsx
    
*   ui/TraceTimeline.tsx
    

**No other files impacted**

7\. Implementation Plan
-----------------------

### Phase 1.1 — Core Telemetry (Week 1)

*   Agent SDK (Python)
    
*   AgentRun + AgentStep schema
    
*   Ingest API
    
*   Postgres persistence
    

### Phase 1.2 — Query & UI (Week 2)

*   Run Explorer
    
*   Trace Timeline
    
*   Failure Breakdown
    
*   Step Latency Stats
    

### Phase 1.3 — Hardening (Week 3)

*   Retry modeling
    
*   Failure → step linkage enforcement
    
*   Index optimization
    
*   Example agent integration
    

8\. Testing Strategy
--------------------

### Unit Tests

*   Step timing accuracy
    
*   Failure classification correctness
    
*   Idempotent ingest behavior
    

### Integration Tests

*   End-to-end agent run ingestion
    
*   Failure scenarios:
    
    *   tool timeout
        
    *   schema failure
        
    *   empty retrieval
        

### Manual Validation

*   Reconstruct failed run visually
    
*   Confirm latency attribution
    
*   Verify no sensitive data stored
    

9\. Observability (of This System)
----------------------------------

### Logging

*   Ingest success/failure
    
*   Schema validation errors
    
*   Dropped telemetry warnings
    

### Metrics

*   runs\_ingested\_total
    
*   ingest\_latency\_p95
    
*   dropped\_runs\_total
    

10\. Known Limitations (Phase-1)
--------------------------------

*   No automatic quality scoring
    
*   No replay capability
    
*   Manual interpretation required for decision quality
    
*   Postgres may not scale indefinitely
    

11\. Future Considerations (Phase-2+)
-------------------------------------

### Potential Enhancements

*   Decision reasoning summaries
    
*   Version diffing
    
*   Replay with mocked tools
    
*   Eval pipelines
    
*   Hosted multi-tenant SaaS
    

12\. Dependencies
-----------------

### Runtime

*   Python 3.10+
    
*   FastAPI
    
*   PostgreSQL
    
*   React
    

### Development

*   pytest
    
*   black / ruff
    
*   docker-compose
    

13\. Security Considerations
----------------------------

*   API key–based auth
    
*   Metadata allow-list enforcement
    
*   No PII or prompt content accepted
    
*   Encrypted DB at rest (deployment dependent)
    

14\. Rollout Strategy
---------------------

1.  Local development with sample agent
    
2.  Internal testing with synthetic failures
    
3.  Staging deployment
    
4.  Limited production rollout
    
5.  Monitoring and feedback loop