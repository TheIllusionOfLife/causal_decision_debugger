"""Synthetic control via convex donor weights."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _solve_weights(target: np.ndarray, donors: np.ndarray) -> np.ndarray:
    n = donors.shape[1]

    def loss(w: np.ndarray) -> float:
        return float(np.sum((target - donors @ w) ** 2))

    w0 = np.full(n, 1.0 / n)
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, 1.0)] * n
    res = minimize(loss, w0, method="SLSQP", constraints=constraints, bounds=bounds)
    return np.clip(res.x, 0.0, 1.0)


def estimate_synthetic_control(
    df: pd.DataFrame,
    *,
    unit_col: str,
    period_col: str,
    outcome_col: str,
    treated_unit: Any,
    treat_period: int,
) -> dict[str, Any]:
    panel = df.pivot_table(index=period_col, columns=unit_col, values=outcome_col)
    panel = panel.sort_index()
    pre = panel.loc[panel.index < treat_period]
    post = panel.loc[panel.index >= treat_period]
    target_pre = pre[treated_unit].values
    donor_cols = [c for c in panel.columns if c != treated_unit]
    donors_pre = pre[donor_cols].values
    weights = _solve_weights(target_pre, donors_pre)

    counterfactual_post = post[donor_cols].values @ weights
    actual_post = post[treated_unit].values
    effects = actual_post - counterfactual_post
    avg_effect = float(np.mean(effects))
    se = float(np.std(effects, ddof=1) / np.sqrt(len(effects))) if len(effects) > 1 else 0.0
    ci_low = avg_effect - 1.96 * se
    ci_high = avg_effect + 1.96 * se

    pre_residuals = target_pre - donors_pre @ weights
    pre_mspe = float(np.mean(pre_residuals**2))
    diagnostics = {
        "pre_period_mspe": {
            "status": "passed" if pre_mspe < 0.01 else "warning",
            "details": f"Pre-period MSPE = {pre_mspe:.5f}",
        },
        "donor_weights": {
            "status": "passed",
            "details": (
                "Weights: "
                + ", ".join(f"{c}={w:.2f}" for c, w in zip(donor_cols, weights, strict=False))
                + f"; sum={float(weights.sum()):.3f}"
            ),
        },
    }

    return {
        "method": "synthetic_control",
        "estimand": "ATT",
        "effect_size": avg_effect,
        "effect_unit": "outcome_units",
        "confidence_interval": [float(ci_low), float(ci_high)],
        "p_value": None,
        "sample_size": len(df),
        "treated_units": 1,
        "control_units": len(donor_cols),
        "confidence_level": "medium" if pre_mspe < 0.05 else "low",
        "diagnostics": diagnostics,
        "interpretation": (
            f"Synthetic control ATT = {avg_effect:+.4f} (95% CI "
            f"[{ci_low:+.4f}, {ci_high:+.4f}]); pre-period MSPE = {pre_mspe:.5f}."
        ),
    }
