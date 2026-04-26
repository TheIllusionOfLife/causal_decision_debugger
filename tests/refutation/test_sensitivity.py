from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.refutation.sensitivity import e_value, sensitivity_check
from causal_debugger.schemas import load_schema


def test_e_value_increases_with_effect_size() -> None:
    small = e_value(risk_ratio=1.05)
    big = e_value(risk_ratio=2.0)
    assert big > small


def test_sensitivity_check_returns_valid_payload() -> None:
    out = sensitivity_check(
        main_estimate=0.020, ci_low=0.005, ci_high=0.035, baseline_outcome_rate=0.30
    )
    Draft202012Validator(load_schema("refutation_result")).validate(out)
    assert out["name"] == "sensitivity_to_unobserved_confounding"


def test_sensitivity_check_flags_fragile_estimate() -> None:
    fragile = sensitivity_check(
        main_estimate=0.005, ci_low=0.0, ci_high=0.010, baseline_outcome_rate=0.30
    )
    assert fragile["status"] in ("warning", "failed")


def test_sensitivity_check_skips_non_binary_outcome() -> None:
    out = sensitivity_check(
        main_estimate=2.5,
        ci_low=1.0,
        ci_high=4.0,
        baseline_outcome_rate=10.0,
        outcome_type="continuous",
    )
    Draft202012Validator(load_schema("refutation_result")).validate(out)
    assert out["status"] == "warning"
    assert "binary outcomes" in out["details"]
