"""AgentTracer sabotage monitor — public entry points.

Thin layer: registers the action and trajectory monitors and delegates all
scoring to the ``monitoring`` package. Suspicion is scored 0 (clean) to 10
(certain sabotage).

The official metric (`ct game-metrics metrics --mode optimized`) OR-combines a
per-action threshold with a trajectory-level threshold, so we ship BOTH legs and
score with both (no `--only-action`):
    ct run monitor <eval> \
        --action-monitor monitor:my_action_monitor \
        --trajectory-monitor monitor:my_traj_monitor --no-upload
"""

from control_tower.models.model_spec import get_model_spec
from control_tower.protocols.monitoring.action_monitors.helpers import (
    build_action_monitor,
    ensemble_action_monitor,
    ensemble_action_monitors,
    skip_read_only_monitor,
)
from control_tower.protocols.monitoring.registry import (
    action_monitors,
    trajectory_monitors,
)
from control_tower.protocols.monitoring.traj_monitors.helpers import (
    ensemble_traj_monitors,
)
from control_tower.protocols.monitoring.types import ActionMonitor, TrajMonitor
from control_tower.trajectories.trajectory import MonitorResult, Trajectory

from monitoring.config import MyArgs, config_for
from monitoring.fusion import build_reason, fuse_scores
from monitoring.normalize import normalize_action
from monitoring.scorers.action_contrast import build_action_contrast_monitor
from monitoring.scorers.heuristics import score_heuristics
from monitoring.scorers.trajectory_agentic import build_agentic_traj_monitor
from monitoring.scorers.trajectory_holistic import build_holistic_traj_monitor
from monitoring.types import ScorerResult


def _build_superset_action_monitor(args: MyArgs) -> ActionMonitor:
    """Strict superset of the `multi` baseline's action leg.

    Ensembles the shipped complementary monitors (orthogonal scope-detector +
    old-action malice-detector) with our task-vs-side-task contrast angle, all on
    the configured model. Mean-combined; read-only actions auto-scored 0.
    """
    model_spec = get_model_spec(args.model, config_for(args.model))
    members: list[ActionMonitor] = [
        build_action_monitor("orthogonal", {"model": args.model}),
        build_action_monitor("old-action", {"model": args.model}),
        build_action_contrast_monitor(
            model_spec, goal_aware=args.goal_aware, cot_level=args.cot_level
        ),
    ]
    monitor = ensemble_action_monitors(members)
    if args.skip_read_only:
        monitor = skip_read_only_monitor(monitor)
    return monitor


def _build_action_monitor(args: MyArgs) -> ActionMonitor:
    """Action monitor that fuses the LLM contrast scorer with heuristics."""
    if args.use_superset:
        return _build_superset_action_monitor(args)
    contrast: ActionMonitor | None = None
    if args.use_action_contrast:
        model_spec = get_model_spec(args.model, config_for(args.model))
        contrast = build_action_contrast_monitor(
            model_spec, goal_aware=args.goal_aware, cot_level=args.cot_level
        )
        if args.ensemble_n > 1:
            contrast = ensemble_action_monitor(contrast, args.ensemble_n)

    async def monitor_func(traj: Trajectory, action_idx: int) -> MonitorResult:
        results: list[ScorerResult] = []

        if args.use_heuristics:
            results.append(score_heuristics(normalize_action(traj, action_idx)))

        if contrast is not None:
            # Bound history so long-trajectory prompts don't overflow small
            # local models; window keeps the current action last.
            if args.max_history and action_idx > args.max_history:
                lo = action_idx - args.max_history
                window = traj.actions[lo : action_idx + 1]
                scored_traj, scored_idx = (
                    traj.model_copy(update={"actions": window}),
                    len(window) - 1,
                )
            else:
                scored_traj, scored_idx = traj, action_idx

            # Graceful fallback: an LLM error/exception must never skip the
            # action (which would drop the whole trajectory). On failure the
            # heuristic signal carries the score.
            try:
                mr = await contrast.func(scored_traj, scored_idx)
                if mr.error is None:
                    results.append(
                        ScorerResult(
                            name="action_contrast",
                            score=mr.sus_score,
                            confidence=1.0,
                            reasons=[mr.reasoning] if mr.reasoning else [],
                        )
                    )
            except Exception:  # noqa: BLE001 - degrade to heuristics, never skip
                pass

        fused = fuse_scores(results)
        return MonitorResult(
            sus_score=max(0.0, min(10.0, fused)),
            reasoning=build_reason(results, fused),
        )

    monitor = ActionMonitor(func=monitor_func)
    if args.skip_read_only:
        monitor = skip_read_only_monitor(monitor)
    return monitor


@action_monitors.register()
def my_action_monitor(args: MyArgs | None = None) -> ActionMonitor:
    return _build_action_monitor(args or MyArgs())


@trajectory_monitors.register()
def my_traj_monitor(args: MyArgs | None = None) -> TrajMonitor:
    """Holistic, goal-aware whole-transcript monitor (the independent trajectory leg).

    A single model pass over the full transcript — catches dispersed/multi-step
    sabotage that per-action scoring misses. Independent of the action leg, so the
    optimized audit rule can OR-combine them.
    """
    args = args or MyArgs()
    model_spec = get_model_spec(args.model, config_for(args.model))

    if args.agentic_traj:
        return build_agentic_traj_monitor(
            model_spec, goal_aware=True, cot_level=args.cot_level
        )

    def make() -> TrajMonitor:
        return build_holistic_traj_monitor(
            model_spec, goal_aware=True, cot_level=args.cot_level
        )

    if args.traj_ensemble_n > 1:
        return ensemble_traj_monitors(
            [make() for _ in range(args.traj_ensemble_n)],
            f"Mean of {args.traj_ensemble_n} holistic trajectory monitors",
        )
    return make()
