from __future__ import annotations

import numpy as np
import statsmodels.api as sm
from jsonschema import Draft202012Validator

from causal_debugger.methods.doubly_robust import estimate_doubly_robust
from causal_debugger.scenarios.dgps import observational_confounding
from causal_debugger.schemas import load_schema


def _naive_ols_ate(df, *, treatment: str, outcome: str, covariates) -> float:
    design = sm.add_constant(
        np.column_stack([df[treatment].astype(float).values, df[list(covariates)].values])
    )
    model = sm.OLS(df[outcome].astype(float).values, design).fit()
    return float(model.params[1])


def test_dr_recovers_ate_on_confounded_data() -> None:
    scen = observational_confounding(n=20_000, seed=20)
    truth = scen.truth["true_ate"]
    out = estimate_doubly_robust(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        covariates=["motivation_proxy", "paid_channel"],
    )
    Draft202012Validator(load_schema("estimate_result")).validate(out)
    assert abs(out["effect_size"] - truth) < 0.015


def test_dr_consistent_with_naive_under_no_confounding() -> None:
    # When confounding is mild and PS is decent, DR and naive are close.
    scen = observational_confounding(n=20_000, seed=20)
    naive = _naive_ols_ate(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        covariates=["motivation_proxy", "paid_channel"],
    )
    out = estimate_doubly_robust(
        scen.frame,
        treatment="treated",
        outcome="outcome",
        covariates=["motivation_proxy", "paid_channel"],
    )
    assert abs(out["effect_size"] - naive) < 0.01
