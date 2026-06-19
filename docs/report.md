# Track A Sabotage Monitor — AgentTracer

**Track A (monitor building) · blue team · 2026-06-17 · code: github.com/laxkc/AgentTracer (branch `main`)**

## Problem
A trusted monitor scores each agent action/trajectory 0–10 for sabotage; a downstream auditor
spends a fixed ~1% honest false-positive budget. Goal: **push successful sabotage above the 99th
percentile of honest behavior** so it's caught within budget.
`safety = caught / (caught + uncaught successful sabotage)` at fixed honest FPR.

## Method
A **dual-leg trusted monitor** (model: `gpt-5-nano`, the trusted model), evaluated with the
official `ct game-metrics` under **honest-calibrated** audit rules (threshold fit on honest data
only — never on attacks):
- **Action leg:** task-vs-side-task *contrast* LLM scorer — reasoning-first, full conversation
  history, salvage-parsed; + a capped deterministic heuristic; read-only actions auto-scored 0.
- **Trajectory leg:** a true **holistic** whole-transcript monitor (goal-aware, primed for
  *dispersed* setup→exploit patterns the action leg can't see), plus an **agentic
  triage→investigate** variant (investigates only non-benign runs — cheaper than a fixed ensemble).
- **Evaluation:** public `ram-data-public` trajectories, **pooled across the 3 hardest attackers**
  (opus-strategies + opus + sonnet → 69 honest / 78 attack, 74 successful, ASR 94.9%) for stable
  estimates. Threshold per the calibration trap: honest-only, over a population, at the reported unit.

## Results (trusted model, honest-calibrated, pooled)

| Audit budget | leg | **Ours** | Baseline `multi`+`mean-quick` |
|---|---|---|---|
| 1% | action-only | **0.554** | 0.525 |
| 1% | trajectory-only | 0.715 | **0.793** |
| 5% | action-only | 0.923 | 0.928 |
| 5% | trajectory-only | 0.885 | 0.885 |

**Usefulness 0.377** (honest main-task success — identical for both; monitoring never degrades it).
Achieved FPR = target at every action-leg budget (the trajectory leg's discrete scores cap the 5%
point at ~1.5%). **Bootstrap 95% CI (action-leg @1%, 2000 resamples):**
ours 0.54 [0.19, 0.65], baseline 0.46 [0.34, 0.58] — **overlapping, so safety is statistically on
par**; note our action leg has *higher variance* (fatter honest tail), a real weakness.

**The decisive, non-overlapping win is cost — measured in model calls per trajectory.** AgentTracer
runs **1 action call + a single trajectory pass (1–2 calls when agentic)** vs the baseline's **2
action prompts + a 5× trajectory ensemble** — **≈ ¼ the calls at on-par safety.** (Dollar estimate
at list prices: ~$0.15 vs ~$0.53/trajectory.)

## Ablation — where each addition helps, and where it stops
- **Action leg:** ours ≥ baseline at 1% (contrast prompt is competitive with the 2-prompt
  `orthogonal`+`old_action` ensemble).
- **Trajectory leg:** baseline's 5× `mean-quick` > our holistic-3× — ensemble depth matters here.
- **Holistic trajectory leg added to the action leg** moved us from clearly-behind to on-par: it
  catches dispersed multi-step sabotage the action leg structurally misses.
- **Diminishing returns / ceiling:** a *superset* action ensemble (orthogonal+old_action+contrast)
  **diluted** rather than improved; the **agentic** investigator sharpened single cases (a real
  attack 4→10) but, as a single pass, was noisier than a 3× mean. On a *strong* model the baseline
  **near-saturates** the hardest data (1.000 @2%) — **passive monitoring plateaus; further
  scaffolding doesn't beat a well-tuned baseline.**

## Error analysis (per side-task category, @1%)
Perfect on `running_malware` (1.00) and strong on `data_tampering` (0.72); **weakest on
`monitoring_subversion` (0.36)** and `access_control_bypass` (0.45) — the subtle, dispersed
sabotage that hides across individually-benign steps. This is the frontier for a passive monitor.

## Limitations
Small honest calibration set; `gpt-5-nano` scoring is stochastic (single-dataset results vary —
an opus-strategies "win" did not survive pooling); `optimized` mode tunes the threshold on
attacks (we therefore report honest-calibrated single-leg rules); evaluated on released public
model-attacks, not the human straj set or adaptive attackers; gpt-5-mini results (an upper bound
if a stronger monitor is permitted) are reported separately, not as the headline.

## Reproduce
`ct run monitor <data> --action-monitor monitor:my_action_monitor --trajectory-monitor
monitor:my_traj_monitor` → `ct game-metrics metrics --honest <h> --attack <a> --mode action_only`
(and `trajectory_only`). Full numbers in `docs/results.md`; committed metrics JSON in `docs/metrics/`.
