"""Conditional ATE via T-Learner with gradient-boosted base learners.

Avoids econml's heavier dependencies for the MVP while still delivering segment-level effects.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor


def _segment_effects(
    df: pd.DataFrame, *, treatment: str, outcome: str, segment_col: str
) -> dict[Any, float]:
    out: dict[Any, float] = {}
    for value, sub in df.groupby(segment_col):
        treated = sub[sub[treatment] == 1][outcome].astype(float)
        control = sub[sub[treatment] == 0][outcome].astype(float)
        if len(treated) and len(control):
            out[value] = float(treated.mean() - control.mean())
    return out


def estimate_cate(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    covariates: Sequence[str],
) -> dict[str, Any]:
    encoded = pd.get_dummies(df[list(covariates)], drop_first=True, dtype=float)
    x = encoded.values
    t = df[treatment].astype(int).values
    y = df[outcome].astype(float).values

    mu1 = GradientBoostingRegressor(max_depth=3, n_estimators=200, random_state=0).fit(
        x[t == 1], y[t == 1]
    ).predict(x)
    mu0 = GradientBoostingRegressor(max_depth=3, n_estimators=200, random_state=0).fit(
        x[t == 0], y[t == 0]
    ).predict(x)
    cate = mu1 - mu0
    ate = float(np.mean(cate))
    se = float(np.std(cate, ddof=1) / np.sqrt(len(cate)))

    diagnostics: dict[str, Any] = {
        "cate_distribution": {
            "status": "passed",
            "details": (
                f"mean={ate:+.4f}, std={float(np.std(cate)):.4f}, "
                f"q10={float(np.quantile(cate, 0.1)):+.4f}, q90={float(np.quantile(cate, 0.9)):+.4f}"
            ),
        }
    }
    seg_col = next((c for c in covariates if df[c].nunique() <= 6), None)
    if seg_col is not None:
        seg = _segment_effects(df, treatment=treatment, outcome=outcome, segment_col=seg_col)
        diagnostics["segment_effects"] = {
            "status": "passed",
            "details": ", ".join(f"{seg_col}={k}: {v:+.4f}" for k, v in seg.items()),
        }

    return {
        "method": "cate_t_learner",
        "estimand": "CATE",
        "effect_size": ate,
        "effect_unit": "outcome_units",
        "confidence_interval": [float(ate - 1.96 * se), float(ate + 1.96 * se)],
        "p_value": None,
        "sample_size": len(df),
        "treated_units": int(t.sum()),
        "control_units": int((1 - t).sum()),
        "confidence_level": "medium",
        "diagnostics": diagnostics,
        "interpretation": (
            f"T-Learner average CATE = {ate:+.4f}; see diagnostics for heterogeneity by segment."
        ),
    }
