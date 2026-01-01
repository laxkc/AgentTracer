Agent Observability Platform — Phase 1 (AI Coding Context)
----------------------------------------------------------

1\. Purpose of This Document
----------------------------

This document provides **authoritative context** for AI coding assistants working on this repository.

Any AI system modifying or generating code **must follow this document** to:

*   stay within Phase-1 scope
    
*   avoid architectural drift
    
*   preserve security and privacy guarantees
    
*   align with production design intent
    

If there is a conflict between code comments and this document, **this document wins**.

2\. What This System Is
-----------------------

This repository implements **Phase-1 of an Agent Observability Platform**.

### High-level goal

> Make AI agent behavior **visible, debuggable, and measurable** in production by capturing structured agent telemetry (runs, steps, failures).

This is **NOT**:

*   a logging system
    
*   a prompt store
    
*   an LLM evaluation platform
    
*   a replay or simulation engine
    

3\. Phase-1 Scope (Hard Constraints)
------------------------------------

### Phase-1 focuses on **visibility**, not intelligence.

The system MUST:

*   Capture agent runs
    
*   Capture ordered steps per run
    
*   Measure latency per step
    
*   Capture **semantic failure classification**
    
*   Provide query + UI for inspection
    

The system MUST NOT:

*   Store raw prompts or LLM responses
    
*   Store chain-of-thought or hidden reasoning
    
*   Perform automatic quality evaluation
    
*   Re-execute agent logic
    
*   Modify agent behavior
    

If a feature touches these forbidden areas, **do not implement it**.

4\. Mental Model (Critical for AI Coding)
-----------------------------------------

### Agent ≠ Microservice

An agent is modeled as:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   Agent Run   ├─ Ordered Steps   │    ├─ plan   │    ├─ retrieve   │    ├─ tool (0..n attempts)   │    ├─ respond   └─ Optional Failure   `

Observability here is **decision-centric**, not infra-centric.

AI code should **always preserve**:

*   step order (seq)
    
*   step boundaries
    
*   per-step timing
    
*   explicit failure attribution
    

5\. Core Domain Concepts (Do Not Rename Casually)
-------------------------------------------------

These concepts are **stable API contracts**:

### AgentRun

*   One execution of an agent
    
*   Identified by run\_id
    
*   Has start/end time
    
*   Has status: success | failure | partial
    

### AgentStep

*   One atomic step in the agent lifecycle
    
*   Ordered by seq
    
*   Has:
    
    *   step\_type (plan, retrieve, tool, respond, etc.)
        
    *   latency\_ms
        
    *   metadata (safe only)
        

### AgentFailure

*   Semantic failure description
    
*   Always classified by:
    
    *   failure\_type
        
    *   failure\_code
        
*   Should reference a step\_id whenever possible
    

Do **not** collapse these into logs or generic events.

6\. Failure Taxonomy (Mandatory)
--------------------------------

Failures MUST be classified using this model:

### failure\_type

*   tool
    
*   model
    
*   retrieval
    
*   orchestration
    

### failure\_code (examples)

*   timeout
    
*   schema\_invalid
    
*   empty\_retrieval
    
*   hallucination
    
*   uncaught\_exception
    

AI code **must not invent free-form failure types**.

If unsure, default to:

*   orchestration / uncaught\_exception
    

7\. Retry Modeling Rules (Very Important)
-----------------------------------------

### Rule

> **Each retry is its own step span.**

Incorrect:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   tool(call_api, retry_count=2)   `

Correct:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   tool(call_api, attempt=1)  tool(call_api, attempt=2)   `

This is required for:

*   accurate latency attribution
    
*   future retry analysis
    
*   UI clarity
    

AI-generated code **must never overwrite step history**.

8\. Privacy & Redaction Rules (Non-Negotiable)
----------------------------------------------

Phase-1 is **privacy-by-default**.

### Allowed to store

*   tool name
    
*   HTTP status codes
    
*   retry counts
    
*   latency
    
*   numeric metadata
    
*   enum/string labels
    

### Forbidden to store

*   raw prompts
    
*   raw LLM responses
    
*   documents or retrieval content
    
*   user PII
    
*   chain-of-thought
    

AI code must **never** introduce fields that store raw text payloads.

9\. Storage & API Constraints
-----------------------------

### Database

*   PostgreSQL is used in Phase-1
    
*   Tables:
    
    *   agent\_runs
        
    *   agent\_steps
        
    *   agent\_failures
        

### API Design

*   Ingest API is **write-only**
    
*   Query API is **read-only**
    
*   Idempotency via run\_id
    

AI code must:

*   avoid schema drift
    
*   avoid cross-table coupling
    
*   keep JSONB usage minimal and intentional
    

10\. SDK Design Rules
---------------------

The SDK must:

*   be lightweight
    
*   be non-blocking
    
*   support async / batched delivery
    
*   fail safely (do not crash agent)
    

The SDK must NOT:

*   inspect prompt contents
    
*   modify agent logic
    
*   enforce business rules
    
*   depend on agent frameworks internally
    

11\. Observability of This System
---------------------------------

AI code should ensure:

*   ingest errors are logged
    
*   dropped telemetry is observable
    
*   query performance is predictable
    

But do NOT:

*   add complex metrics systems
    
*   add tracing to tracing (keep it simple)
    

12\. How AI Should Make Changes
-------------------------------

When modifying or adding code, AI must:

1.  State **what Phase-1 requirement this supports**
    
2.  Ensure **no forbidden data is introduced**
    
3.  Preserve existing semantics
    
4.  Prefer **explicitness over cleverness**
    
5.  Avoid speculative features
    

If unsure → **ask or leave a TODO comment** instead of guessing.

13\. What Success Looks Like (Phase-1)
--------------------------------------

This system is successful if an engineer can:

*   Open the UI
    
*   Click a failed agent run
    
*   See:
    
    *   step order
        
    *   step latency
        
    *   tool retries
        
    *   failure classification
        
*   Understand _why_ the agent failed in under 60 seconds
    

Anything not supporting this is out of scope.

14\. Future Phases (Awareness Only)
-----------------------------------

AI may see TODOs referencing:

*   Phase-2 reasoning summaries
    
*   Phase-2 version diffing
    
*   Phase-2 replay
    

These are **NOT** to be implemented in Phase-1.

15\. Final Instruction to AI Systems
------------------------------------

> **Do not optimize prematurely.Do not expand scope.Do not store sensitive data.Do not guess agent intent.**

Phase-1 exists to **make behavior visible**, not to make agents smarter.