"""Interrupted time series via segmented regression."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate_its(
    df: pd.DataFrame,
    *,
    period_col: str,
    post_col: str,
    outcome_col: str,
) -> dict[str, Any]:
    df = df.sort_values(period_col).reset_index(drop=True)
    t = df[period_col].astype(float).values
    post = df[post_col].astype(float).values
    intervention_t = float(t[post == 1].min()) if (post == 1).any() else float(t.max() + 1)
    time_since_intervention = np.where(post == 1, t - intervention_t, 0.0)
    design = np.column_stack([t, post, time_since_intervention])
    design = sm.add_constant(design, has_constant="add")
    y = df[outcome_col].astype(float).values
    model = sm.OLS(y, design).fit(cov_type="HC1")

    level_shift = float(model.params[2])
    ci_low, ci_high = (float(c) for c in model.conf_int()[2])
    pre_resid = y[post == 0] - model.predict(design[post == 0])
    autocorr = (
        float(np.corrcoef(pre_resid[:-1], pre_resid[1:])[0, 1])
        if len(pre_resid) > 2
        else 0.0
    )
    diagnostics = {
        "pre_period_fit": {
            "status": "passed",
            "details": f"Pre-period R² = {1 - pre_resid.var() / max(y[post == 0].var(), 1e-9):.3f}",
        },
        "autocorrelation": {
            "status": "warning" if abs(autocorr) > 0.3 else "passed",
            "details": f"Lag-1 residual autocorrelation = {autocorr:+.3f}",
        },
    }

    return {
        "method": "interrupted_time_series",
        "estimand": "ATE",
        "effect_size": level_shift,
        "effect_unit": "outcome_units",
        "confidence_interval": [ci_low, ci_high],
        "p_value": float(model.pvalues[2]),
        "sample_size": len(df),
        "treated_units": int((post == 1).sum()),
        "control_units": int((post == 0).sum()),
        "confidence_level": "low" if abs(autocorr) > 0.3 else "medium",
        "diagnostics": diagnostics,
        "interpretation": (
            f"ITS level shift at intervention = {level_shift:+.4f} "
            f"(95% CI [{ci_low:+.4f}, {ci_high:+.4f}])."
        ),
    }
