from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.methods.ipw import estimate_ipw
from causal_debugger.scenarios.dgps import observational_confounding, poor_overlap
from causal_debugger.schemas import load_schema


def test_ipw_recovers_ate_on_confounded_data() -> None:
    scen = observational_confounding(n=20_000)
    out = estimate_ipw(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        covariates=["motivation_proxy", "paid_channel"],
    )
    assert abs(out["effect_size"] - scen.truth["true_ate"]) < 0.01
    Draft202012Validator(load_schema("estimate_result")).validate(out)


def test_ipw_warns_on_poor_overlap() -> None:
    scen = poor_overlap(n=20_000)
    out = estimate_ipw(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        covariates=["paid_channel"],
    )
    assert out["diagnostics"]["propensity_overlap"]["status"] in ("warning", "failed")
