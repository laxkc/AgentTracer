"""Monitor configuration (``MyArgs``).

Model routing (see ``control_tower/models/model_spec.py``): self-hosted prefixes
``{vllm, sglang, hf, ollama, openai-api}`` bypass OpenRouter; everything else routes
to OpenRouter. The default monitor model is the trusted model (gpt-5-nano via
OpenRouter). Override per run, e.g.::

    ct run monitor <eval> --action-monitor monitor:my_action_monitor \
        --action-monitor-arg model=openai/gpt-5-mini --only-action
"""

from inspect_ai.model import GenerateConfig

from control_tower.trajectories.format_history import CotLevel
from control_tower.utils.function_registry.base_model import BaseModelPython

# Canonical trusted monitor model (gpt-5-nano via OpenRouter). Default for all runs.
TRUSTED_MODEL = "trusted"

# Optional free local model (OpenAI-compatible vLLM/llama.cpp), used only when a
# local server is running and explicitly selected. The ``openai-api/<name>/<model>``
# form makes Inspect read ``VLLM_BASE_URL`` / ``VLLM_API_KEY`` and is self-hosted,
# so it never routes through OpenRouter.
LOCAL_MODEL = "openai-api/vllm/qwen3-coder-next"

# Bounded generation for a slow local model: cap output (the prompt emits a short
# response), fail fast on hangs, and avoid long retry backoff. temperature=0 gives
# deterministic, reproducible scoring — local models are noisy at the default
# temperature, so greedy decoding is preferred over averaging samples.
LOCAL_CONFIG = GenerateConfig(max_tokens=512, timeout=90, max_retries=1, temperature=0.0)

# Config for OpenRouter reasoning models (e.g. gpt-5-nano, the trusted model):
# they spend the token budget on internal reasoning, so max_tokens must leave room
# for the visible answer, and reasoning_effort is kept low for cost/latency.
TRUSTED_CONFIG = GenerateConfig(max_tokens=8192, reasoning_effort="low", timeout=180, max_retries=2)

# Model-name prefixes that hit a self-hosted (local) endpoint.
_SELF_HOSTED = ("vllm/", "openai-api/", "sglang/", "hf/", "ollama/")


def config_for(model: str) -> GenerateConfig:
    """Pick the generation config appropriate to where the model runs."""
    return LOCAL_CONFIG if model.startswith(_SELF_HOSTED) else TRUSTED_CONFIG


class MyArgs(BaseModelPython):
    """Suspicion is scored 0-10 (float). Defaults to the trusted model (gpt-5-nano)."""

    # Model alias/name (string), overridable per run, e.g.
    #   --action-monitor-arg model=openai/gpt-5-mini
    #   --action-monitor-arg model=vllm/qwen3-coder-next   (if a local server is up)
    # Defaults to the trusted model (gpt-5-nano via OpenRouter) — the canonical
    # monitor model. Resolved to a ModelSpec via config_for() in monitor.py.
    model: str = TRUSTED_MODEL
    cot_level: CotLevel = "none"

    # Superset action leg: ensemble the shipped orthogonal + old-action monitors
    # with our contrast scorer. Off by default — in testing it diluted rather than
    # improved the result; kept available for ablation.
    use_superset: bool = False

    # Agentic trajectory leg: triage then investigate near-threshold cases
    # (cheaper than a fixed ensemble; sharper at the strict tail). Default traj leg.
    agentic_traj: bool = True

    # Which scorers contribute to the per-action fused score (non-superset path).
    use_action_contrast: bool = True
    use_heuristics: bool = True

    # Goal-aware prompts inject every side-task goal for the environment;
    # goal-agnostic prompts infer suspicion from main-task deviation alone.
    goal_aware: bool = False

    # Average N samples of the action LLM scorer to reduce variance (1 = off).
    ensemble_n: int = 1

    # Ensemble the holistic trajectory monitor over N independent passes (mean),
    # like the shipped `mean-quick`. Reduces variance and improves sensitivity of
    # the trajectory leg, which is decisive at higher budgets.
    traj_ensemble_n: int = 3

    # Prior-action history fed to the LLM scorer. 0 = full history (default):
    # long, subtle attacks need full context to detect. Set a positive cap only
    # for small local models that would overflow on long prompts.
    max_history: int = 0

    # Auto-score pure read-only actions (view / ls / cat) as 0 without an LLM call.
    skip_read_only: bool = True
