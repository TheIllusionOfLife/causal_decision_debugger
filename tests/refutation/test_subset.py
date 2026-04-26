from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.methods.ab_test import estimate_ab
from causal_debugger.refutation.subset import subset_stability
from causal_debugger.scenarios.dgps import randomized_ab
from causal_debugger.schemas import load_schema


def test_subset_stability_passes_for_random_data() -> None:
    scen = randomized_ab(n=20_000, seed=5)
    df = scen.frame.copy()
    df["segment"] = (df["country"] == "US").astype(int)

    def estimator(sub):
        return estimate_ab(sub, treatment="treated", outcome="outcome")["effect_size"]

    out = subset_stability(df, segment_col="segment", estimator=estimator, main_estimate=0.020)
    Draft202012Validator(load_schema("refutation_result")).validate(out)
    assert out["status"] in ("passed", "warning")
