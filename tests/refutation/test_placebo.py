from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.refutation.placebo import placebo_treatment_test
from causal_debugger.scenarios.dgps import randomized_ab
from causal_debugger.schemas import load_schema


def test_placebo_treatment_returns_null_effect() -> None:
    scen = randomized_ab(n=10_000, seed=4)
    out = placebo_treatment_test(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        main_estimate=0.020,
        seed=0,
    )
    Draft202012Validator(load_schema("refutation_result")).validate(out)
    assert out["name"] == "placebo_treatment"
    assert abs(out["delta_vs_main_estimate"]) > 0.0
    assert out["status"] in ("passed", "warning")


def test_placebo_treatment_warns_on_large_placebo_effect() -> None:
    scen = randomized_ab(n=200, seed=99)
    out = placebo_treatment_test(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        main_estimate=0.020,
        threshold=0.0001,
        seed=0,
    )
    assert out["status"] in ("warning", "failed")
