"""Render the Safety-vs-audit-budget curve from a `ct game-metrics` metrics.json.

Reads a multi-run metrics file (one subset per run, each with a `budgets` list)
and writes a PNG plotting safety (y) against audit budget % (x, log scale).

Usage:
    uv run python monitoring/eval/plot_safety_curve.py \
        --metrics docs/metrics/compare.json \
        --out docs/figures/safety_vs_budget.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True, help="path to metrics.json")
    ap.add_argument("--out", required=True, help="output PNG path")
    args = ap.parse_args()

    data = json.loads(Path(args.metrics).read_text())

    fig, ax = plt.subplots(figsize=(12, 8))
    all_budgets = set()
    for subset in data["subsets"]:
        label = subset.get("run_label") or subset.get("group_value") or "run"
        budgets = sorted(subset["budgets"], key=lambda b: b["budget_pct"])
        xs = [b["budget_pct"] for b in budgets]
        ys = [b["safety"] for b in budgets]
        all_budgets.update(xs)
        # marker is essential: a single-budget run is one point and would be
        # invisible as a line-only plot (a line needs >=2 points).
        ax.plot(xs, ys, linewidth=2.5, marker="o", markersize=7, label=label)

    ax.set_xscale("log")
    ax.set_xlabel("Audit budget", fontsize=14)
    ax.set_ylabel("Safety", fontsize=14)
    ax.set_title("Safety vs Target FPR", fontsize=16)
    ax.set_ylim(0.0, 1.05)
    # Label ticks at exactly the audit budgets present, as clean percentages;
    # suppress matplotlib's default log minor-tick sci-notation (e.g. "2x10^0").
    ticks = sorted(all_budgets)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{v:g}%" for v in ticks])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=12)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100, bbox_inches="tight")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
