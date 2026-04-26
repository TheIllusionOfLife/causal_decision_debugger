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


def test_placebo_treatment_warns_when_treatment_is_single_class() -> None:
    scen = randomized_ab(n=200, seed=1)
    df = scen.frame.copy()
    df["treated"] = 1  # collapse to a single class
    out = placebo_treatment_test(df, treatment="treated", outcome="outcome", main_estimate=0.020)
    assert out["status"] == "warning"
    assert "one class" in out["details"]


def test_placebo_treatment_uses_estimator_callback() -> None:
    scen = randomized_ab(n=2_000, seed=2)
    captured: list[int] = []

    def fake_estimator(permuted) -> float:  # type: ignore[no-untyped-def]
        captured.append(int(permuted["treated"].sum()))
        return 0.0

    out = placebo_treatment_test(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        main_estimate=0.020,
        estimator=fake_estimator,
    )
    assert captured, "estimator callback should be invoked"
    assert out["status"] == "passed"
