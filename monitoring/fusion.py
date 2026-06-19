"""Fuse per-scorer results into one 0-10 action score.

V1: confidence-weighted weighted average (system_design_full.md §16). Each
scorer's static weight is scaled by its confidence (floored at 0.25 so a
low-confidence scorer still contributes a little).
"""

from monitoring.types import ScorerResult

# Only scorers that actually exist. The LLM contrast scorer is the primary
# signal; heuristics are a weak deterministic prior. Confidence-weighting
# (below) makes action_contrast dominate ~4:1 in practice.
DEFAULT_WEIGHTS: dict[str, float] = {
    "action_contrast": 0.80,
    "heuristics": 0.20,
}

_CONFIDENCE_FLOOR = 0.25


def fuse_scores(
    results: list[ScorerResult],
    weights: dict[str, float] | None = None,
) -> float:
    """Confidence-weighted blend of scorer scores; 0.0 if nothing contributes."""
    weights = weights or DEFAULT_WEIGHTS
    weighted_sum = 0.0
    total_weight = 0.0

    for result in results:
        weight = weights.get(result.name, 0.0)
        if weight <= 0.0:
            continue
        weight *= max(_CONFIDENCE_FLOOR, result.confidence)
        weighted_sum += weight * result.score
        total_weight += weight

    if total_weight == 0.0:
        return 0.0
    return weighted_sum / total_weight


def build_reason(results: list[ScorerResult], fused: float, top_k: int = 2) -> str:
    """Human-readable explanation, surfacing the highest-scoring contributors."""
    ordered = sorted(results, key=lambda r: r.score, reverse=True)
    parts: list[str] = [f"fused={fused:.2f}"]
    for r in ordered[:top_k]:
        reason = r.reasons[0] if r.reasons else ""
        parts.append(f"{r.name}={r.score:.1f}(c{r.confidence:.2f}): {reason}")
    return " | ".join(parts)
