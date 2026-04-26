"""Difference-in-differences estimator with a parallel-trends test."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm


def _pre_trend_test(
    df: pd.DataFrame, *, group_col: str, period_col: str, outcome_col: str, treat_period: int
) -> dict[str, Any]:
    pre = df[df[period_col] < treat_period].copy()
    if pre.empty or period_col not in pre.columns:
        return {"status": "warning", "details": "No pre-period data available."}
    design = pd.DataFrame(
        {
            "const": 1.0,
            "group": pre[group_col].astype(float),
            "period": pre[period_col].astype(float),
            "group_x_period": pre[group_col].astype(float) * pre[period_col].astype(float),
        }
    )
    model = sm.OLS(pre[outcome_col].astype(float).values, design.values).fit(cov_type="HC1")
    coef = float(model.params[3])
    pval = float(model.pvalues[3])
    if pval < 0.05 and abs(coef) > 1e-4:
        return {
            "status": "warning",
            "details": (
                f"Pre-trend interaction is significant (coef={coef:+.4f}, p={pval:.4f}); "
                "parallel-trends assumption is suspect."
            ),
        }
    return {
        "status": "passed",
        "details": f"No significant pre-trend (coef={coef:+.4f}, p={pval:.4f}).",
    }


def estimate_did(
    df: pd.DataFrame,
    *,
    group_col: str,
    post_col: str,
    outcome_col: str,
    period_col: str | None = "period",
) -> dict[str, Any]:
    g = df[group_col].astype(float).values
    p = df[post_col].astype(float).values
    interaction = g * p
    design = sm.add_constant(np.column_stack([g, p, interaction]), has_constant="add")
    y = df[outcome_col].astype(float).values
    model = sm.OLS(y, design).fit(cov_type="HC1")
    eff = float(model.params[-1])
    ci_low, ci_high = (float(c) for c in model.conf_int()[-1])
    treated_units = int(df[df[group_col] == 1][outcome_col].count())
    control_units = int(df[df[group_col] == 0][outcome_col].count())

    diagnostics: dict[str, Any] = {}
    pretrend_status = "passed"
    if period_col is not None and period_col in df.columns:
        treat_period = int(np.median(df[df[post_col] == 1][period_col].astype(int)))
        # Parallel-trends check on the pre-period.
        diagnostics["pre_trend_test"] = _pre_trend_test(
            df,
            group_col=group_col,
            period_col=period_col,
            outcome_col=outcome_col,
            treat_period=treat_period,
        )
        pretrend_status = diagnostics["pre_trend_test"]["status"]
    else:
        diagnostics["pre_trend_test"] = {
            "status": "warning",
            "details": "No period column supplied; cannot test parallel trends.",
        }
        pretrend_status = "warning"

    confidence = "medium"
    if pretrend_status == "warning":
        confidence = "low"

    return {
        "method": "difference_in_differences",
        "estimand": "ATT",
        "effect_size": eff,
        "effect_unit": "outcome_units",
        "confidence_interval": [ci_low, ci_high],
        "p_value": float(model.pvalues[-1]),
        "sample_size": len(df),
        "treated_units": treated_units,
        "control_units": control_units,
        "confidence_level": confidence,
        "diagnostics": diagnostics,
        "interpretation": (
            f"DiD estimate of ATT = {eff:+.4f} (95% CI [{ci_low:+.4f}, {ci_high:+.4f}]) "
            "under parallel trends."
        ),
    }
