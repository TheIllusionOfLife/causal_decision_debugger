"""Report-quality gate: forbid overclaim phrases unless confidence is high."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from causal_debugger.reporting.render import render_report

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "onboarding_retention"

FORBIDDEN_PHRASES = [
    r"\bproved that\b",
    r"\bdefinitely caused\b",
    r"\bguaranteed impact\b",
    r"caused .{1,40}? to (increase|decrease)",
]


def _ctx(confidence: str = "medium") -> dict:
    return {
        "analysis_id": "onboarding_retention_2026_03",
        "causal_spec": yaml.safe_load((EXAMPLE / "causal_spec.yaml").read_text()),
        "assumption_ledger": yaml.safe_load((EXAMPLE / "assumption_ledger.yaml").read_text()),
        "method_plan": {
            "primary_method": "doubly_robust_estimation",
            "secondary_methods": ["propensity_score_weighting"],
            "identifiability_status": "weakly_identifiable",
            "reasoning_summary": "Observational with rich covariates.",
        },
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
            "confidence_level": confidence,
            "diagnostics": {},
            "interpretation": "Estimated effect is +2.1 pp.",
        },
        "refutation": [],
    }


def test_report_lacks_forbidden_phrases_under_medium_confidence() -> None:
    report = render_report(_ctx("medium")).lower()
    for pattern in FORBIDDEN_PHRASES:
        assert not re.search(pattern, report), f"forbidden phrase matched: {pattern}"


def test_report_renders_required_sections() -> None:
    report = render_report(_ctx("medium"))
    for header in (
        "Executive Summary",
        "Confidence Level",
        "Assumption Ledger Summary",
        "Recommended Decision",
        "Recommended Next Experiment or Data Collection",
    ):
        assert header in report


def test_report_carries_confidence_level() -> None:
    for level in ("medium", "low"):
        report = render_report(_ctx(level)).lower()
        assert level in report
