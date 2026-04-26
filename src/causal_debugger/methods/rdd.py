"""Local linear regression discontinuity estimator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm


def _local_linear(
    df: pd.DataFrame, running_var: str, outcome: str, cutoff: float, bandwidth: float
) -> tuple[float, float, float]:
    sub = df[(df[running_var] >= cutoff - bandwidth) & (df[running_var] <= cutoff + bandwidth)]
    centered = sub[running_var].astype(float).values - cutoff
    treated = (sub[running_var] >= cutoff).astype(int).values
    interaction = treated * centered
    design = sm.add_constant(np.column_stack([treated, centered, interaction]))
    y = sub[outcome].astype(float).values
    model = sm.OLS(y, design).fit(cov_type="HC1")
    eff = float(model.params[1])
    ci = model.conf_int(alpha=0.05)
    return eff, float(ci[1, 0]), float(ci[1, 1])


def estimate_rdd(
    df: pd.DataFrame,
    *,
    running_var: str,
    outcome: str,
    cutoff: float,
    bandwidth: float | None = None,
) -> dict[str, Any]:
    span = float(df[running_var].max() - df[running_var].min())
    if bandwidth is None:
        bandwidth = span / 4
    eff, ci_low, ci_high = _local_linear(df, running_var, outcome, cutoff, bandwidth)
    half = bandwidth / 2
    eff_half, _, _ = _local_linear(df, running_var, outcome, cutoff, half)
    eff_double, _, _ = _local_linear(df, running_var, outcome, cutoff, min(bandwidth * 2, span))

    sensitivity_max = max(abs(eff - eff_half), abs(eff - eff_double))
    bw_status = "passed" if sensitivity_max < abs(eff) * 0.3 + 1e-3 else "warning"
    diagnostics = {
        "bandwidth_sensitivity": {
            "status": bw_status,
            "details": (
                f"Effect at h={bandwidth:.3f}: {eff:+.4f}; at h/2: {eff_half:+.4f}; "
                f"at 2h: {eff_double:+.4f}"
            ),
        }
    }

    treated_n = int((df[running_var] >= cutoff).sum())
    control_n = int((df[running_var] < cutoff).sum())
    return {
        "method": "regression_discontinuity",
        "estimand": "LATE",
        "effect_size": eff,
        "effect_unit": "outcome_units",
        "confidence_interval": [ci_low, ci_high],
        "p_value": None,
        "sample_size": len(df),
        "treated_units": treated_n,
        "control_units": control_n,
        "confidence_level": "medium" if bw_status == "passed" else "low",
        "diagnostics": diagnostics,
        "interpretation": (
            f"Local linear RDD jump at cutoff = {eff:+.4f} (95% CI "
            f"[{ci_low:+.4f}, {ci_high:+.4f}], bandwidth={bandwidth:.3f})."
        ),
    }
