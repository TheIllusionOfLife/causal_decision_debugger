"""Instrumental variables (2SLS) via linearmodels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd
from linearmodels.iv import IV2SLS


def estimate_iv(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    instrument: str,
    exogenous: Sequence[str] = (),
) -> dict[str, Any]:
    work = df.copy()
    work["__const"] = 1.0
    exog_cols = ["__const", *list(exogenous)]
    model = IV2SLS(
        dependent=work[outcome].astype(float),
        exog=work[exog_cols].astype(float),
        endog=work[[treatment]].astype(float),
        instruments=work[[instrument]].astype(float),
    ).fit(cov_type="robust")

    eff = float(model.params[treatment])
    ci = model.conf_int().loc[treatment]
    ci_low, ci_high = float(ci.iloc[0]), float(ci.iloc[1])
    p_value = float(model.pvalues[treatment])

    first_stage = model.first_stage.diagnostics
    f_stat = float(first_stage.iloc[0]["f.stat"])
    weak_threshold = 10.0
    f_status = "passed" if f_stat >= weak_threshold else "warning"

    diagnostics = {
        "first_stage_F": {
            "status": f_status,
            "details": (
                f"Cragg-Donald F = {f_stat:.2f} "
                f"(threshold for weak instrument: {weak_threshold})"
            ),
        }
    }
    confidence = "medium" if f_status == "passed" else "low"

    return {
        "method": "instrumental_variables",
        "estimand": "LATE",
        "effect_size": eff,
        "effect_unit": "outcome_units",
        "confidence_interval": [ci_low, ci_high],
        "p_value": p_value,
        "sample_size": len(df),
        "treated_units": int(df[treatment].sum()),
        "control_units": int((df[treatment] == 0).sum()),
        "confidence_level": confidence,
        "diagnostics": diagnostics,
        "interpretation": (
            f"2SLS LATE = {eff:+.4f} (95% CI [{ci_low:+.4f}, {ci_high:+.4f}]); "
            f"first-stage F = {f_stat:.2f}."
        ),
    }
