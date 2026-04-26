"""Render decision-grade reports from artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _format_assumptions(ledger: dict[str, Any] | None) -> str:
    if not ledger:
        return "_No assumption ledger available._"
    rows = []
    for entry in ledger.get("assumptions", []):
        rows.append(
            f"- **[{entry['id']}] {entry['name']}** — status: `{entry['status']}`, "
            f"importance: `{entry['importance']}`. {entry.get('evidence', '').strip()}"
        )
    return "\n".join(rows) if rows else "_No assumptions recorded._"


def _format_refutation(items: list[dict[str, Any]] | None) -> str:
    if not items:
        return "_No refutation checks have been run._"
    rows = []
    for item in items:
        delta = item.get("delta_vs_main_estimate")
        delta_str = f" (Δ vs main: {delta:+.4f})" if isinstance(delta, int | float) else ""
        rows.append(f"- **{item['name']}** — `{item['status']}`. {item['details']}{delta_str}")
    return "\n".join(rows)


def _format_diagnostics(diag: dict[str, Any] | None) -> str:
    if not diag:
        return ""
    rows = []
    for name, body in diag.items():
        rows.append(f"- {name}: `{body['status']}` — {body['details']}")
    return "\n".join(rows)


def _identifiability_section(failure: dict[str, Any]) -> str:
    reasons = "\n".join(f"- {r}" for r in failure["reasons"])
    return (
        "## Result: Not Identifiable With Current Data\n\n"
        "This question cannot be answered causally from the current data.\n\n"
        f"**Reasons:**\n\n{reasons}\n\n"
        "## Recommended Next Action\n\n"
        f"{failure['recommended_next_action']}\n"
    )


def _confidence_rationale(estimate: dict[str, Any], plan: dict[str, Any]) -> str:
    level = estimate["confidence_level"]
    if level == "high":
        return "Randomized or strong quasi-experimental design with passing diagnostics."
    if level == "medium":
        return (
            "Observational or quasi-experimental design with reasonable diagnostics but "
            "meaningful assumption risk: " + plan.get("reasoning_summary", "")
        )
    if level == "low":
        return "Serious confounding, weak comparison group, or unstable diagnostics."
    return "The available data and design cannot answer the causal question."


def render_report(ctx: dict[str, Any]) -> str:
    spec = ctx["causal_spec"]
    plan = ctx.get("method_plan") or {}
    estimate = ctx.get("estimate")
    failure = ctx.get("identifiability_failure")
    causal_q = spec.get("causal_question", {})
    treatment = causal_q.get("treatment", {})
    outcome = causal_q.get("outcome", {})
    business = spec.get("business_decision", {})

    parts: list[str] = [f"# {ctx.get('analysis_id', spec.get('analysis_id', 'analysis'))} — Causal Decision Report\n"]

    if failure is not None:
        parts.append(_identifiability_section(failure))
        parts.append("## Decision Context\n\n" + business.get("question", ""))
        parts.append("## Causal Question\n")
        parts.append(f"- **Unit:** {causal_q.get('unit', '')}")
        parts.append(f"- **Treatment:** {treatment.get('name', '')}")
        parts.append(f"- **Outcome:** {outcome.get('name', '')}")
        parts.append(f"- **Comparison group:** {causal_q.get('comparison_group', '')}\n")
        parts.append("## Data Used\n\n" + (spec.get("data", {}).get("local_path") or "see causal_spec.yaml"))
        parts.append("## Method Summary\n")
        parts.append(f"- **Identifiability:** `{plan.get('identifiability_status', 'not_identifiable')}`")
        parts.append(f"- **Reasoning:** {plan.get('reasoning_summary', '')}\n")
        parts.append("## Main Result\n\nNot identifiable with current data.\n")
        parts.append("## Confidence Level\n\n**not_identifiable** — see reasons above.\n")
        parts.append("## Assumption Ledger Summary\n\n" + _format_assumptions(ctx.get("assumption_ledger")))
        parts.append("\n## Robustness and Refutation Checks\n\n_Skipped: no estimate was produced._")
        parts.append("\n## Limitations\n\nThe current data cannot identify the causal effect.")
        parts.append("\n## Recommended Decision\n\nDo not declare causal impact. Run the recommended next action.")
        parts.append("\n## Recommended Next Experiment or Data Collection\n\n" + failure["recommended_next_action"])
        parts.append("\n## Technical Appendix\n\nSee `technical_appendix.md`.\n")
        return "\n".join(parts)

    if estimate is None:
        raise ValueError("render_report requires either estimate or identifiability_failure in ctx")

    parts.append("## Executive Summary\n")
    parts.append(estimate.get("interpretation", "(no interpretation supplied)"))
    parts.append(
        f"\n**Confidence:** {estimate['confidence_level']}.\n"
    )

    parts.append("## Decision Context\n\n" + business.get("question", ""))
    parts.append("\n## Causal Question\n")
    parts.append(f"- **Unit:** {causal_q.get('unit', '')}")
    parts.append(f"- **Treatment:** {treatment.get('name', '')}")
    parts.append(f"- **Outcome:** {outcome.get('name', '')}")
    parts.append(f"- **Comparison group:** {causal_q.get('comparison_group', '')}\n")

    data = spec.get("data") or {}
    parts.append("## Data Used\n\n" + (data.get("local_path") or "see causal_spec.yaml"))

    parts.append("\n## Method Summary\n")
    parts.append(f"- **Primary method:** `{plan.get('primary_method', estimate['method'])}`")
    parts.append(
        f"- **Secondary methods:** `{', '.join(plan.get('secondary_methods', [])) or 'none'}`"
    )
    parts.append(f"- **Identifiability:** `{plan.get('identifiability_status', 'unknown')}`\n")

    ci_low, ci_high = estimate["confidence_interval"]
    parts.append("## Main Result\n")
    parts.append(
        f"Estimated **{estimate['estimand']} = {estimate['effect_size']:+.4f} "
        f"{estimate['effect_unit']}** (95% CI [{ci_low:+.4f}, {ci_high:+.4f}])."
    )
    if estimate.get("p_value") is not None:
        parts.append(f"\np-value: {estimate['p_value']:.4f}.")
    parts.append(
        f"\nSample size: {estimate['sample_size']:,} ({estimate['treated_units']:,} treated / "
        f"{estimate['control_units']:,} control)."
    )
    diag_md = _format_diagnostics(estimate.get("diagnostics"))
    if diag_md:
        parts.append("\n**Diagnostics:**\n" + diag_md)

    parts.append(
        f"\n## Confidence Level\n\n**{estimate['confidence_level']}** — "
        + _confidence_rationale(estimate, plan)
    )

    parts.append("\n## Assumption Ledger Summary\n\n" + _format_assumptions(ctx.get("assumption_ledger")))
    parts.append("\n## Robustness and Refutation Checks\n\n" + _format_refutation(ctx.get("refutation")))

    limitations = ctx.get("limitations") or (
        "Treatment was not confirmed randomized; unobserved confounding may remain. "
        "See assumption ledger for the load-bearing assumptions."
    )
    parts.append("\n## Limitations\n\n" + limitations)

    decision = ctx.get("recommended_decision") or (
        "Provisionally accept the estimated effect under the stated assumptions. "
        "Consider a randomized holdout before declaring final impact."
    )
    parts.append("\n## Recommended Decision\n\n" + decision)

    next_step = ctx.get("recommended_next_step") or (
        "Run a 10% randomized holdout for 14 days, or instrument the next launch with a staggered rollout."
    )
    parts.append("\n## Recommended Next Experiment or Data Collection\n\n" + next_step)

    parts.append("\n## Technical Appendix\n\nSee `technical_appendix.md`.\n")
    return "\n".join(parts)


def render_from_dir(analysis_dir: Path) -> str:
    analysis_dir = Path(analysis_dir).resolve()
    spec = yaml.safe_load((analysis_dir / "causal_spec.yaml").read_text())
    ledger_path = analysis_dir / "assumption_ledger.yaml"
    ledger = yaml.safe_load(ledger_path.read_text()) if ledger_path.exists() else None
    plan_path = analysis_dir / "method_plan.json"
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else None
    estimates_path = analysis_dir / "artifacts" / "estimates.json"
    estimate = json.loads(estimates_path.read_text()) if estimates_path.exists() else None
    failure_path = analysis_dir / "artifacts" / "identifiability_failure.json"
    failure = json.loads(failure_path.read_text()) if failure_path.exists() else None
    refute_path = analysis_dir / "artifacts" / "robustness.json"
    refutation = json.loads(refute_path.read_text()) if refute_path.exists() else None
    ctx = {
        "analysis_id": spec.get("analysis_id"),
        "causal_spec": spec,
        "assumption_ledger": ledger,
        "method_plan": plan,
        "estimate": estimate,
        "identifiability_failure": failure,
        "refutation": refutation,
    }
    return render_report(ctx)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    text = render_from_dir(args.analysis_dir)
    if args.out:
        out = args.out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
