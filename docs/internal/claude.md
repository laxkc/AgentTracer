Phase 3 — Behavioral Drift Detection & Guardrails
-------------------------------------------------

Purpose
-------

This document defines **how AI coding assistants (Claude Code)** must be used when working on **Phase 3** of the Agent Observability Platform.

Phase 3 is **analysis-only**, **read-only**, and **non-interventional**.

Claude is permitted to:

*   assist with **derivation logic**
    
*   generate **queries**
    
*   create **visualization logic**
    
*   help reason about **statistical drift**
    

Claude is **not permitted** to:

*   invent agent behavior
    
*   suggest agent fixes
    
*   introduce control loops
    
*   infer reasoning or intent
    

Core Rule (Non-Negotiable)
--------------------------

> **Claude may only help observe and describe agent behavior — never influence, evaluate, or optimize it.**

If a Claude-generated change:

*   modifies agent execution
    
*   prescribes actions
    
*   judges correctness
    
*   introduces feedback loops
    

→ **Reject the change.**

Phase 3 Scope (What Claude Is Allowed to Work On)
-------------------------------------------------

Claude **may assist with**:

### ✅ Allowed Domains

*   Drift detection logic
    
*   Baseline comparison algorithms
    
*   Statistical aggregation
    
*   Trend analysis
    
*   Visualization components
    
*   Alert threshold definitions
    
*   Read-only APIs
    
*   Derived data models
    
*   Documentation
    

### ❌ Forbidden Domains

*   Prompt engineering
    
*   Agent logic
    
*   Retry policies
    
*   Tool selection logic
    
*   Auto-remediation
    
*   Quality scoring
    
*   “Health” metrics
    
*   Agent ranking
    
*   Recommendations or fixes
    

Data Access Rules
-----------------

Claude **must assume**:

*   ❌ No access to prompts
    
*   ❌ No access to responses
    
*   ❌ No access to reasoning text
    
*   ❌ No access to user input
    
*   ❌ No access to retrieved documents
    

All Phase 3 inputs are:

*   Aggregated
    
*   Structured
    
*   Privacy-safe
    
*   Derived from Phase 2 only
    

If Claude proposes accessing raw data → **invalid**.

Mental Model Claude Must Follow
-------------------------------

Claude must reason using this pipeline only:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   Phase 2 Data     ↓  Historical Baseline     ↓  Observed Distribution     ↓  Statistical Comparison     ↓  Drift Signal   `

Claude **must not** introduce:

*   Causal claims
    
*   Optimization logic
    
*   Decision enforcement
    

Only **observed change** is allowed.

Drift Semantics (Strict)
------------------------

Claude must treat “drift” as:

> A statistically significant change in a distribution relative to a baseline.

Claude **must not** equate drift with:

*   failure
    
*   bug
    
*   regression
    
*   correctness
    
*   quality
    

Drift is **descriptive**, not evaluative.

Language Constraints (Very Important)
-------------------------------------

Claude must use **neutral, observational language only**.

### ✅ Approved Language

*   “Observed increase”
    
*   “Distribution shifted”
    
*   “Correlates with”
    
*   “Detected deviation”
    
*   “Baseline comparison shows”
    

### ❌ Forbidden Language

*   “Better / Worse”
    
*   “Correct / Incorrect”
    
*   “Optimal / Suboptimal”
    
*   “Fix this”
    
*   “Agent should”
    
*   “Improve performance”
    

If Claude outputs judgmental language → **rewrite required**.

Alerts & Notifications
----------------------

Claude may help design alerts **only if**:

*   Alerts are informational
    
*   Alerts describe _what changed_
    
*   Alerts reference the baseline
    
*   Alerts do not prescribe actions
    

Claude must never suggest:

*   automatic rollback
    
*   retry tuning
    
*   logic changes
    
*   human instructions
    

Code Generation Rules
---------------------

Claude-generated code **must**:

*   Be read-only with respect to Phase 1 & 2 data
    
*   Use explicit typing
    
*   Include docstrings
    
*   Avoid side effects
    
*   Be deterministic
    
*   Avoid hidden heuristics
    

Claude-generated code **must not**:

*   Write to agent tables
    
*   Modify agent state
    
*   Call agent SDKs
    
*   Trigger workflows
    

Statistical Discipline
----------------------

Claude may propose:

*   KS tests
    
*   Chi-square tests
    
*   Jensen–Shannon divergence
    
*   Percent delta thresholds
    
*   Time-window comparisons
    

Claude **must**:

*   Explain assumptions
    
*   Avoid overfitting
    
*   Avoid “magic thresholds”
    
*   Allow human override
    

UI & Visualization Rules
------------------------

Claude may help generate:

*   Charts
    
*   Tables
    
*   Dashboards
    

But must ensure:

*   No single “health score”
    
*   No rankings
    
*   No recommendations
    
*   No prescriptive annotations
    

Visuals must be:

*   Comparative
    
*   Time-based
    
*   Distribution-oriented
    

Failure Scenarios Claude Must Anticipate
----------------------------------------

Claude should proactively consider:

*   Sparse data
    
*   Cold start baselines
    
*   Seasonal behavior
    
*   Legitimate behavior changes
    
*   Version rollouts
    

Claude **must not** assume drift = problem.

Human-in-the-Loop Boundary
--------------------------

Claude’s responsibility ends at **visibility**.

Claude must never:

*   decide action
    
*   suggest fixes
    
*   automate responses
    

All interpretation belongs to humans.

Review Checklist for Claude Output
----------------------------------

Before accepting Claude-generated changes, verify:

*   No agent behavior modification
    
*   No privacy boundary violations
    
*   No evaluative language
    
*   No feedback loops
    
*   No optimization logic
    
*   Phase 1 & 2 untouched
    
*   Purely additive changes
    
*   Observational semantics preserved
    

If any check fails → **reject**.

One-Line Rule for Claude
------------------------

> **Claude helps humans notice change — not decide what to do about it.**

End of claude.md
----------------

This file defines **how AI assistance is safely used** in Phase 3.

It is intentionally strict.