"""A/B test estimator: difference in means + optional regression adjustment."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def _diagnostic(status: str, details: str) -> dict[str, Any]:
    return {"status": status, "details": details}


def _diff_in_means(df: pd.DataFrame, *, treatment: str, outcome: str) -> dict[str, Any]:
    treat = df[df[treatment] == 1][outcome].astype(float)
    control = df[df[treatment] == 0][outcome].astype(float)
    n_t, n_c = len(treat), len(control)
    if n_t == 0 or n_c == 0:
        raise ValueError("A/B analysis requires both treated and control units.")
    if n_t < 2 or n_c < 2:
        raise ValueError(
            f"A/B analysis requires at least 2 observations per arm (got n_t={n_t}, n_c={n_c})."
        )
    diff = float(treat.mean() - control.mean())
    var_t = float(treat.var(ddof=1))
    var_c = float(control.var(ddof=1))
    se = math.sqrt(var_t / n_t + var_c / n_c)
    if se == 0.0:
        # Both arms are constant. p=1 when diff=0, otherwise the test is degenerate.
        p = 1.0 if diff == 0.0 else 0.0
        ci_low = ci_high = diff
    else:
        z = diff / se
        p = 2 * (1 - stats.norm.cdf(abs(z)))
        ci_low = diff - 1.96 * se
        ci_high = diff + 1.96 * se
    return {
        "effect_size": diff,
        "se": se,
        "ci": (float(ci_low), float(ci_high)),
        "p_value": float(p),
        "n_t": int(n_t),
        "n_c": int(n_c),
    }


def _regression_adjusted(
    df: pd.DataFrame, *, treatment: str, outcome: str, covariates: Sequence[str]
) -> dict[str, Any]:
    design = pd.get_dummies(df[list(covariates)], drop_first=True, dtype=float)
    design.insert(0, "treatment", df[treatment].astype(float).values)
    design = sm.add_constant(design, has_constant="add")
    y = df[outcome].astype(float).values
    model = sm.OLS(y, design.values, missing="drop").fit(cov_type="HC1")
    idx = list(design.columns).index("treatment")
    eff = float(model.params[idx])
    ci_low, ci_high = (float(c) for c in model.conf_int()[idx])
    return {
        "effect_size": eff,
        "se": float(model.bse[idx]),
        "ci": (ci_low, ci_high),
        "p_value": float(model.pvalues[idx]),
        "n_t": int((df[treatment] == 1).sum()),
        "n_c": int((df[treatment] == 0).sum()),
    }


def estimate_ab(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    covariates: Sequence[str] | None = None,
) -> dict[str, Any]:
    if covariates:
        method = "regression_adjustment"
        out = _regression_adjusted(df, treatment=treatment, outcome=outcome, covariates=covariates)
    else:
        method = "ab_test_analysis"
        out = _diff_in_means(df, treatment=treatment, outcome=outcome)
    treat_rate = float(df[treatment].mean())
    sample_ratio_warning = abs(treat_rate - 0.5) > 0.05
    diagnostics = {
        "sample_ratio": _diagnostic(
            "warning" if sample_ratio_warning else "passed",
            f"Treated share: {treat_rate:.3f}",
        )
    }
    confidence = "high"
    if sample_ratio_warning:
        confidence = "medium"
    return {
        "method": method,
        "estimand": "ATE",
        "effect_size": out["effect_size"],
        "effect_unit": "outcome_units",
        "confidence_interval": [out["ci"][0], out["ci"][1]],
        "p_value": out["p_value"],
        "sample_size": len(df),
        "treated_units": out["n_t"],
        "control_units": out["n_c"],
        "confidence_level": confidence,
        "diagnostics": diagnostics,
        "interpretation": (
            f"Estimated ATE = {out['effect_size']:+.4f} (95% CI "
            f"[{out['ci'][0]:+.4f}, {out['ci'][1]:+.4f}]) under randomized assignment."
        ),
    }


def cuped(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    pre_metric: str,
) -> dict[str, Any]:
    """CUPED variance-reduction adjustment using a pre-treatment covariate."""
    y = df[outcome].astype(float).values
    x = df[pre_metric].astype(float).values
    theta = float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)) if np.var(x) > 0 else 0.0
    adjusted = pd.Series(y - theta * (x - x.mean()), index=df.index)
    new_df = df.assign(_cuped_outcome=adjusted)
    return estimate_ab(new_df, treatment=treatment, outcome="_cuped_outcome")
