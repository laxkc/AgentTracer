"""Internal data types for scoring and fusion.

These are *internal*: the control-tower ``MonitorResult`` only carries
``sus_score`` + ``reasoning``, so confidence / evidence / per-scorer detail
live here and never leave the monitor boundary.
"""

from pydantic import BaseModel, Field


class NormalizedAction(BaseModel):
    """A scorer-friendly view of one ``control_tower`` ``Action``."""

    idx: int
    tool_name: str | None = None
    action_summary: str = ""
    tool_input: str | None = None

    files_touched: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)
    diff_summary: str | None = None

    output_summary: str | None = None
    output_error: str | None = None
    reasoning_text: str | None = None

    risk_tags: list[str] = Field(default_factory=list)


class ScorerResult(BaseModel):
    """Output of a single scorer (one action)."""

    name: str
    score: float  # 0.0 - 10.0
    confidence: float = 1.0  # 0.0 - 1.0
    reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
