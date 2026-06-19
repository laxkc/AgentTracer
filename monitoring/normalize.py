"""Convert control-tower ``Action`` objects into ``NormalizedAction``.

Pure, deterministic, no model calls — safe to run anywhere. Only reads fields
confirmed to exist on ``Action`` (function, arguments, output, output_error,
agent_reasoning, extended_thinking, index).
"""

import json
from typing import Any

from control_tower.trajectories.trajectory import Action, Trajectory

from monitoring.types import NormalizedAction

# Risk-tag hints (from system_design_full.md §10), keyed to the kinds of
# behaviour side tasks tend to touch in this benchmark.
RISK_PATTERNS: dict[str, list[str]] = {
    "notification": ["notify", "notification", "alert", "email", "followup"],
    "safety": ["safety", "adverse", "incident", "risk", "reaction"],
    "auth": ["auth", "permission", "role", "token", "secret", "credential"],
    "logging": ["log", "audit", "trace", "monitor"],
    "validation": ["validate", "schema", "check", "guard"],
    "filtering": ["filter", "suppress", "ignore", "skip"],
    "config": ["config", "env", "flag", "setting"],
    "test": ["test", "assert", "fixture", "mock"],
}

_MAX_FIELD_CHARS = 600


def _clip(text: str, limit: int = _MAX_FIELD_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + " …[clipped]"


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)


def _extract_files(function: str | None, args: dict[str, Any]) -> list[str]:
    files: list[str] = []
    path = args.get("path")
    if isinstance(path, str):
        files.append(path)
    for key in ("file_path", "filename", "target_file"):
        val = args.get(key)
        if isinstance(val, str):
            files.append(val)
    return list(dict.fromkeys(files))


def _extract_commands(function: str | None, args: dict[str, Any]) -> list[str]:
    if function != "bash":
        return []
    cmd = args.get("cmd")
    if not isinstance(cmd, str):
        raw = args.get("command")
        cmd = raw if isinstance(raw, str) else None
    return [cmd] if cmd else []


def _diff_summary(function: str | None, args: dict[str, Any]) -> str | None:
    if function != "text_editor":
        return None
    command = args.get("command")
    if command == "str_replace":
        old = _stringify(args.get("old_str"))
        new = _stringify(args.get("new_str"))
        return _clip(f"str_replace\n- {old}\n+ {new}")
    if command == "create":
        return _clip(f"create file:\n{_stringify(args.get('file_text'))}")
    if command == "insert":
        return _clip(f"insert @ line {args.get('insert_line')}:\n{_stringify(args.get('new_str'))}")
    return None


def _risk_tags(text: str) -> list[str]:
    low = text.lower()
    return [tag for tag, kws in RISK_PATTERNS.items() if any(k in low for k in kws)]


def normalize_action(traj: Trajectory, idx: int) -> NormalizedAction:
    """Build a ``NormalizedAction`` for ``traj.actions[idx]``."""
    action: Action = traj.actions[idx]
    args = action.arguments or {}

    files = _extract_files(action.function, args)
    commands = _extract_commands(action.function, args)
    diff = _diff_summary(action.function, args)

    tool_input = _clip(_stringify(args))
    summary_bits = [f"tool={action.function}"]
    if files:
        summary_bits.append(f"files={files}")
    if commands:
        summary_bits.append(f"cmd={_clip(commands[0], 200)}")
    action_summary = "; ".join(summary_bits)

    reasoning = action.agent_reasoning or action.extended_thinking

    tag_source = " ".join(
        [action.function or "", tool_input, " ".join(files), reasoning or ""]
    )

    return NormalizedAction(
        idx=idx,
        tool_name=action.function,
        action_summary=action_summary,
        tool_input=tool_input,
        files_touched=files,
        commands_run=commands,
        diff_summary=diff,
        output_summary=_clip(action.output) if action.output else None,
        output_error=action.output_error,
        reasoning_text=_clip(reasoning) if reasoning else None,
        risk_tags=_risk_tags(tag_source),
    )
