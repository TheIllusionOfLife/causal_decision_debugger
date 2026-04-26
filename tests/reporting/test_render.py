"""Tests for report rendering."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from causal_debugger.reporting.render import render_report

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "onboarding_retention"


def _ctx() -> dict:
    return {
        "analysis_id": "onboarding_retention_2026_03",
        "causal_spec": yaml.safe_load((EXAMPLE / "causal_spec.yaml").read_text()),
        "assumption_ledger": yaml.safe_load((EXAMPLE / "assumption_ledger.yaml").read_text()),
        "method_plan": json.loads((EXAMPLE / "method_plan.json").read_text()),
        "estimate": {
            "method": "doubly_robust_estimation",
            "estimand": "ATE",
            "effect_size": 0.021,
            "effect_unit": "percentage_points",
            "confidence_interval": [0.008, 0.034],
            "p_value": 0.012,
            "sample_size": 20000,
            "treated_units": 8000,
            "control_units": 12000,
            "confidence_level": "medium",
            "diagnostics": {
                "covariate_balance": {"status": "passed", "details": "All SMDs < 0.1"},
                "propensity_overlap": {"status": "warning", "details": "Tails are thin."},
            },
            "interpretation": (
                "Under the stated assumptions, onboarding_v2 likely increased D7 retention "
                "by about 2.1 percentage points."
            ),
        },
        "refutation": [
            {
                "name": "placebo_outcome",
                "status": "passed",
                "details": "No effect on pre-treatment activity proxy.",
                "delta_vs_main_estimate": 0.0,
            }
        ],
    }


def test_render_returns_required_sections() -> None:
    report = render_report(_ctx())
    for header in (
        "Executive Summary",
        "Decision Context",
        "Causal Question",
        "Data Used",
        "Method Summary",
        "Main Result",
        "Confidence Level",
        "Assumption Ledger Summary",
        "Robustness and Refutation Checks",
        "Limitations",
        "Recommended Decision",
        "Recommended Next Experiment or Data Collection",
    ):
        assert header in report, f"missing section: {header}"


def test_render_includes_confidence_value() -> None:
    report = render_report(_ctx())
    assert "medium" in report.lower()


def test_render_no_overclaim_when_not_high() -> None:
    report = render_report(_ctx())
    forbidden = ["proved that", "definitely caused", "guaranteed impact"]
    for phrase in forbidden:
        assert phrase.lower() not in report.lower()


def test_render_handles_not_identifiable() -> None:
    ctx = _ctx()
    ctx["estimate"] = None
    ctx["identifiability_failure"] = {
        "identifiability_status": "not_identifiable",
        "reasons": ["No comparison group exists.", "No pre-period available."],
        "recommended_next_action": "Run a 10% randomized holdout for 14 days.",
        "method_attempted": None,
    }
    report = render_report(ctx)
    assert "Not Identifiable" in report
    assert "10% randomized holdout" in report
    assert "Recommended next action" in report.lower() or "recommended" in report.lower()
