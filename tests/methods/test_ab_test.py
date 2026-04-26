from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.methods.ab_test import estimate_ab
from causal_debugger.scenarios.dgps import randomized_ab
from causal_debugger.schemas import load_schema


def test_ab_recovers_known_ate() -> None:
    scen = randomized_ab(n=20_000)
    result = estimate_ab(scen.frame, treatment="treated", outcome="outcome")
    assert abs(result["effect_size"] - scen.truth["true_ate"]) < 0.005


def test_ab_result_validates_against_schema() -> None:
    scen = randomized_ab(n=5_000)
    result = estimate_ab(scen.frame, treatment="treated", outcome="outcome")
    Draft202012Validator(load_schema("estimate_result")).validate(result)


def test_ab_with_covariates_returns_consistent_estimate() -> None:
    scen = randomized_ab(n=10_000)
    result = estimate_ab(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        covariates=["country", "device_type"],
    )
    assert abs(result["effect_size"] - scen.truth["true_ate"]) < 0.01
    assert result["method"] == "regression_adjustment"


def test_ab_confidence_high_when_balanced() -> None:
    scen = randomized_ab(n=5_000)
    result = estimate_ab(scen.frame, treatment="treated", outcome="outcome")
    assert result["confidence_level"] == "high"
