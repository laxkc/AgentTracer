Best Practices & Behavioral Guide for Claude-based Coding
---------------------------------------------------------

**Project:** Agent Observability Platform — Phase 1

🧠 1. High-Level Intent (What You Are Building)
-----------------------------------------------

You are building an **Agent Observability Platform Phase-1 MVP** with these capabilities:

### Observability Goals

*   Capture **structured agent runs**
    
*   Record **ordered steps with latency**
    
*   Detect semantic **failures with taxonomy**
    
*   Enable UI to show:
    
    *   run list
        
    *   step timeline
        
    *   failure breakdown
        
    *   step latency stats
        

### Key Principles

*   Strict **privacy by default**
    
*   No raw prompts or raw responses
    
*   Reliable ingestion and query APIs
    
*   Minimal but accurate telemetry
    
*   Easy debugging and visual inspection
    

📜 2. Claude’s Code Generation Mission
--------------------------------------

When asked to generate or modify code, **always follow this pattern**:

1.  **Restate Intent**Begin by stating which requirement or design principle the change satisfies.
    
2.  **Scope Restriction**Ensure code changes stay within **Phase-1 MVP scope**:
    
    *   No prompt storage
        
    *   No automatic eval
        
    *   No replay
        
    *   No chain-of-thought retention
        
3.  **Safety First**⚠ Code must never introduce:
    
    *   Raw prompts
        
    *   Raw outputs
        
    *   PII
        
    *   Chain-of-thought
        
4.  **Explicit Reasoning Explanation**Provide internal reasoning comments (in natural language) about why a piece of code satisfies the design.
    
5.  **Testable, Self-Documented Code**Include:
    
    *   clear type hints
        
    *   docstrings
        
    *   examples where necessary
        

🚧 3. Hard Constraints (Non-Negotiable)
---------------------------------------

### ❌ Forbidden

*   Storing any text that could reveal prompts or LLM output
    
*   Capturing chain of thought
    
*   Feature-creep beyond Phase-1 telemetry
    

### ✅ Mandatory

*   Steps must be ordered with seq
    
*   Failures must attach to a step\_id
    
*   Retries must be separate step spans
    
*   Structured failure types only (no free-form strings)
    
*   No response rewriting logic
    

⚙️ 4. Behavioral Coding Guidelines
----------------------------------

### 4.1 Naming & Types

Follow these conventions:

*   AgentRun, AgentStep, AgentFailure must be consistent with design doc
    
*   Use strict enum sets for:
    
    *   step\_type
        
    *   failure\_type
        
    *   failure\_code
        

Example:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   StepType = Literal["plan", "retrieve", "tool", "respond"]  FailureType = Literal["tool", "model", "retrieval", "orchestration"]   `

### 4.2 API Contract Enforcement

#### Ingest API (POST /v1/runs)

*   Must validate:
    
    *   run\_id UUID
        
    *   steps array with increasing seq
        
    *   failure object if present
        

Do not relax schema constraints.

### 4.3 Data Storage

#### Postgres Schema (Phase-1)

Tables must include:

*   agent\_runs
    
*   agent\_steps
    
*   agent\_failures
    

Do not add prompt text columns.

### 4.4 SDK Rules

The SDK must:

*   Generate step spans automatically
    
*   Accept safe metadata only
    
*   Associate failures with steps
    
*   Batch send telemetry
    

Do not infer intent or modify agent logic.

🧪 5. Testing & Validation
--------------------------

Every code change must include:

### Unit Tests

*   Validate schema enforcement
    
*   Test failure classification behavior
    
*   Test retry modeling rules
    

### Integration Tests

*   Simulate real agent runs (including retries)
    
*   Ensure telemetry persists and is queryable
    
*   Ensure UI can reconstruct timelines
    

Testing must avoid actual NLP calls (mock where necessary).

📈 6. Observability of the Observability System
-----------------------------------------------

You should add observability _about_ the telemetry system itself:

**Metrics**

*   runs\_ingested\_total
    
*   ingest\_latency\_p95
    
*   dropped\_runs\_total
    

**Logs**

*   Ingest success / failure
    
*   Schema validation errors
    

These should _not_ include sensitive info.

🧠 7. Code Structure & Project Modularity
-----------------------------------------

### Backend (FastAPI)

*   ingest.py: Ingest routes + schema validation
    
*   query.py: Query routes + stats endpoints
    
*   models.py: DB models + migrations
    

### SDK (Python)

*   agenttrace.py: Tracer + context managers
    
*   telemetry.py: Async sender
    

### UI (React)

*   RunExplorer.tsx
    
*   TraceTimeline.tsx
    

Each module must be self-contained and clearly documented.

🤖 8. Claude-specific Prompting Rules
-------------------------------------

When generating new code:

1.  “This code implements the Phase-1 requirement to capture ordered telemetry runs.”
    
2.  **Cite Constraints**Include at least one reference to:
    
    *   privacy constraint
        
    *   retry modeling
        
    *   failure taxonomy
        
3.  **Comment Rationale**Add comments explaining the design choice.
    
4.  **Example Input/Output**Show test cases where applicable.
    

📌 9. Example Good Prompt to Claude
-----------------------------------

> _“Generate the FastAPI /v1/runs ingest route. The route must validate the AgentRun schema with ordered steps, map failures to a step ID, and persist to Postgres. Do not store prompts or responses. Include unit tests for schema validation. Comment on why privacy constraints are upheld.”_

This ensures results follow design.

🧩 10. Example Bad Prompt to Claude
-----------------------------------

❌ _“Add a feature to store raw prompts from agent runs for debugging.”_This violates Phase-1 privacy rules.

Claude should refuse or suggest an alternative approach (e.g., storing safe metadata only).

🛡 11. Handling Ambiguity
-------------------------

If Claude is asked to implement something:

*   think: “Does it strictly improve Phase-1 observability without violating privacy?”
    
*   if answer is **no** → **do not implement**
    

Instead, provide a short TODO with rationale:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # TODO: Phase-2 Feature — requires revisit   `

📜 12. Acceptance Criteria for AI Output
----------------------------------------

Every code snippet must:✔ Compile / run✔ Respect design constraints✔ Come with tests✔ Be documented✔ Not introduce forbidden data capture