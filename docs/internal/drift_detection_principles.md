# Behavioral Drift Detection - Design Principles

## Purpose of This Document

This document defines the **conceptual boundaries, assumptions, and invariants** for the behavioral drift detection capability of the AgentTracer platform.

It exists to ensure that:

- Contributors understand what drift detection is for
- Future changes do not violate core principles
- Drift detection does not silently evolve into an agent control system

If a proposed change contradicts this document, the change should be rejected or redesigned.

## System Context

The AgentTracer platform provides three integrated capabilities:

| Capability | Responsibility |
|-----------|---------------|
| Execution Observability | Execution visibility (runs, steps, failures) |
| Decision & Quality Observability | Decision and quality signal visibility |
| Behavioral Drift Detection | Behavioral stability and change visibility |

Drift detection **does not introduce new telemetry**. It **derives meaning from existing decision and quality data**.

Drift detection is **purely analytical and observational**, not behavioral.

## Core Question

> **"Has the agent's behavior changed in a way that humans should pay attention to?"**

Drift detection does **not** answer:

- Is the agent correct?
- Is the agent good?
- Should the agent be fixed?
- What should the agent do next?

Those remain **human decisions**.

## Fundamental Assumptions

Drift detection is built on the following assumptions:

1. **Agents do not fail loudly**
   - Most agent regressions are behavioral, not infrastructural
   - Execution success does not imply acceptable behavior

2. **Single runs are meaningless**
   - Only distributions over time reveal problems
   - Drift detection ignores individual events entirely

3. **Change matters more than absolute values**
   - A retry rate of 20% may be fine
   - A jump from 5% → 20% is significant

4. **Humans remain accountable**
   - Drift detection never takes action on agents
   - It only informs humans when attention is warranted

## Non-Negotiable Invariants

The following rules must **never be violated**.

### Observational Only

Drift detection must:

- Never modify agent behavior
- Never block agent execution
- Never auto-tune prompts or logic
- Never enforce policies

Drift detection may:

- Compute statistics
- Detect distribution changes
- Emit alerts
- Visualize trends

### Privacy Preservation

Drift detection must **not introduce new data collection**.

It must:

- Never access prompts
- Never access responses
- Never infer reasoning
- Never inspect user content

All inputs are:

- Aggregated
- Structured
- Privacy-safe

### Additive Architecture

Drift detection must:

- Never modify core telemetry tables
- Never modify decision or quality tables
- Never alter ingest semantics

It may:

- Add new derived tables
- Add read-only queries
- Add analysis layers

## Mental Model: How Drift Detection Works

Drift detection introduces **behavioral baselines**.

```
Stable historical behavior
     ↓
Baseline snapshot
     ↓
Live observed behavior
     ↓
Distribution comparison
     ↓
Drift detected (or not)
```

There is no feedback loop.

Drift detection is a **dead-end observer**.

## What "Drift" Means (Precisely)

Drift means:

> A statistically significant change in a behavioral distribution relative to a baseline.

Drift does **not** mean:

- Failure
- Bug
- Regression
- Incorrectness

It only means:

- "This behavior is different than before"

Interpretation is external.

## Scope of Drift Detection

Drift detection may detect drift in:

- Decision distributions (e.g., tool usage, retry strategy selection)
- Quality signal rates (e.g., empty retrievals, schema failures)
- Behavioral latency patterns (not infrastructure latency)

Drift detection must **not**:

- Rank agents
- Score agents
- Aggregate into a single "health" number

## Alerts: Philosophy & Constraints

Alerts are:

- Informational
- Non-blocking
- Non-judgmental

Alerts must:

- Describe what changed
- Reference the baseline used
- Avoid prescribing fixes

Alerts must **never**:

- Trigger automatic actions
- Suggest solutions
- Imply blame

## Human-in-the-Loop Boundary

Drift detection ends where human reasoning begins.

```
Drift detection detects drift
     ↓
Human investigates
     ↓
Human decides whether to act
```

Any proposal that crosses this boundary is **out of scope**.

## Failure Modes This Addresses

Drift detection specifically targets:

- Silent behavioral regressions
- Gradual degradation after deployments
- Cost-inefficient success paths
- Over-retrying or under-retrying agents
- Unexpected changes in decision patterns

It is **not designed** to catch:

- Syntax errors
- Infrastructure outages
- Prompt hallucinations in single runs

## What Drift Detection Intentionally Ignores

Drift detection explicitly ignores:

- Individual agent runs
- User-level satisfaction
- Prompt text
- Model internals
- LLM reasoning traces

This is intentional and non-negotiable.

## Design Philosophy Summary

Drift detection follows three principles:

1. **Stability over optimization**
2. **Visibility over control**
3. **Change detection over judgment**

If drift detection ever:

- tells the agent what to do
- grades agent intelligence
- modifies execution

then it has failed its purpose.

## One-Sentence Definition

> **Drift detection provides early visibility into agent behavioral change, without influencing agent behavior or human decision-making.**

## How to Use This Document

Before implementing or reviewing drift detection changes, ask:

1. Does this introduce new data collection?
2. Does this influence agent behavior?
3. Does this prescribe actions?
4. Does this reduce human accountability?

If the answer to **any** is "yes", the change is invalid.

## Boundary Definition

This document defines the **hard boundary** of drift detection.

Everything inside this boundary is acceptable. Everything outside it violates the design principles.
