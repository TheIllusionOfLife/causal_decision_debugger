from __future__ import annotations

from jsonschema import Draft202012Validator

from causal_debugger.methods.matching import estimate_matching
from causal_debugger.scenarios.dgps import observational_confounding
from causal_debugger.schemas import load_schema


def test_matching_recovers_ate() -> None:
    # Average across seeds: matching with PS-only is noisy on small samples.
    estimates = []
    truth = None
    for seed in (1, 7, 13, 21, 30):
        scen = observational_confounding(n=20_000, seed=seed)
        truth = scen.truth["true_ate"]
        out = estimate_matching(
            scen.frame,
            treatment="treated",
            outcome="outcome",
            covariates=["motivation_proxy", "paid_channel"],
            k=5,
        )
        estimates.append(out["effect_size"])
        Draft202012Validator(load_schema("estimate_result")).validate(out)
    avg = sum(estimates) / len(estimates)
    assert abs(avg - truth) < 0.015, f"avg={avg:.4f} vs truth={truth}"
