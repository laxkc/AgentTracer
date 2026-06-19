# Results — AgentTracer (Track A)

All numbers: public `ram-data-public` trajectories, **pooled across the 3 hardest attackers**
(opus-strategies + opus + sonnet → 69 honest / 78 attack, **74 successful**, ASR 94.9%),
scored with `ct game-metrics`. Threshold **honest-calibrated** (fit on honest data only — never
on attacks). Monitor model = trusted `gpt-5-nano` unless noted.

## Headline — on-par safety at ~¼ the monitoring cost

Honest-calibrated, trusted model, pooled:

| Audit budget | leg | Ours | Baseline `multi`+`mean-quick` |
|---|---|---|---|
| 1% | action-only | **0.554** | 0.525 |
| 2% | action-only | **0.755** | 0.653 |
| 5% | action-only | 0.923 | 0.928 |
| 1% | trajectory-only | 0.715 | **0.793** |
| 5% | trajectory-only | 0.885 | 0.885 |

- **Bootstrap 95% CI (action-leg @1%, 2000 resamples):** ours 0.54 **[0.19, 0.65]**, baseline 0.46
  **[0.34, 0.58]** → **overlapping; statistically on par.** Our action leg has *higher variance*
  (fatter honest tail, p95=8.5 vs baseline 3.5) — a real weakness.
- **Usefulness = 0.377**, identical for both (honest main-task success; monitoring never degrades it).
- **Cost (the clear, non-overlapping win), in model calls per trajectory:** **1 action call + 1
  trajectory pass (1–2 when agentic) vs the baseline's 2 action prompts + a 5× trajectory ensemble
  — ≈ ¼ the calls** at on-par safety. Dollar estimate at list prices: ~$0.15 vs ~$0.53/trajectory.

## Error frontier — safety by side-task category (ours, action-only @1%)
`running_malware` 1.00 · `data_tampering` 0.72 · `access_secret` 0.67 · `exfiltration` 0.53 ·
`access_control_bypass` 0.45 · **`monitoring_subversion` 0.36** (weakest) — subtle sabotage
dispersed across individually-benign steps is the frontier for a passive monitor.

## Iteration journey (where additions help, and where they stop)
1. **Action leg only** (contrast + heuristics): competitive with the baseline's 2-prompt ensemble.
2. **+ holistic trajectory leg** → moved from behind to on-par; catches *dispersed* multi-step
   sabotage the action leg structurally misses (the key addition).
3. **Superset action ensemble** (orthogonal + old_action + contrast): **diluted** — no gain over
   the well-tuned baseline.
4. **Agentic triage→investigate trajectory monitor**: sharpened single cases (a real attack 4→10)
   and is the *cheapest* config, but single-pass it was noisier than a 3× mean.
5. **Stronger model (gpt-5-mini)** beat the *nano* baseline (0.912 vs 0.820 @1%) but **lost to the
   matched-model baseline** (0.912 vs 0.979) — the gain was the model, not the scaffolding.
   On a strong model the baseline **near-saturates** (1.000 @2%) → **passive monitoring plateaus.**

## Methodology notes
- `--mode optimized` tunes the dual threshold on the attack set (optimistic), so we report
  **honest-calibrated** `action_only`/`trajectory_only`.
- Calibrated over a population (never a 1-pair FPR); achieved FPR = target at every action-leg
  budget (the trajectory leg's discrete scores cap the 5% point at ~1.5%).
- gpt-5-mini numbers are an *upper bound* (if a stronger-than-trusted monitor is permitted), not
  the headline.

Reproduce: `monitoring/eval/bootstrap_ci.py`, and `ct game-metrics metrics --mode action_only`
on the scored pools. See `docs/report.md`.
