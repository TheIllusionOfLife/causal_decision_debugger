from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.methods.did import estimate_did
from causal_debugger.scenarios.dgps import parallel_trends_did, violated_pretrends_did
from causal_debugger.schemas import load_schema


def test_did_recovers_ate_under_parallel_trends() -> None:
    scen = parallel_trends_did()
    out = estimate_did(
        scen.frame, group_col="group", post_col="post", outcome_col="outcome"
    )
    assert abs(out["effect_size"] - scen.truth["true_ate"]) < 0.01
    Draft202012Validator(load_schema("estimate_result")).validate(out)


def test_did_warns_on_violated_pretrends() -> None:
    scen = violated_pretrends_did()
    out = estimate_did(
        scen.frame, group_col="group", post_col="post", outcome_col="outcome"
    )
    diag = out["diagnostics"]["pre_trend_test"]
    assert diag["status"] in ("warning", "failed")


def test_did_diagnostics_include_pretrend_test() -> None:
    scen = parallel_trends_did()
    out = estimate_did(
        scen.frame, group_col="group", post_col="post", outcome_col="outcome"
    )
    assert "pre_trend_test" in out["diagnostics"]
