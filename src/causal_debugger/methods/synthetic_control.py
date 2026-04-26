"""Synthetic control via convex donor weights."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _solve_weights(target: np.ndarray, donors: np.ndarray) -> tuple[np.ndarray, bool]:
    n = donors.shape[1]

    def loss(w: np.ndarray) -> float:
        return float(np.sum((target - donors @ w) ** 2))

    w0 = np.full(n, 1.0 / n)
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, 1.0)] * n
    res = minimize(loss, w0, method="SLSQP", constraints=constraints, bounds=bounds)
    weights = np.clip(res.x, 0.0, 1.0)
    total = float(weights.sum())
    weights = weights / total if total > 0 else w0
    return weights, bool(res.success)


def _placebo_distribution(
    panel: pd.DataFrame,
    *,
    treated_unit: Any,
    treat_period: int,
    actual_effect: float,
) -> np.ndarray:
    donor_cols = [c for c in panel.columns if c != treated_unit]
    pre = panel.loc[panel.index < treat_period]
    post = panel.loc[panel.index >= treat_period]
    placebo_effects: list[float] = []
    for placebo in donor_cols:
        others = [c for c in donor_cols if c != placebo]
        if not others:
            continue
        target_pre = pre[placebo].values
        donors_pre = pre[others].values
        weights, success = _solve_weights(target_pre, donors_pre)
        if not success:
            continue
        cf = post[others].values @ weights
        eff = float(np.mean(post[placebo].values - cf))
        placebo_effects.append(eff)
    if not placebo_effects:
        placebo_effects = [actual_effect]
    return np.asarray(placebo_effects, dtype=float)


def estimate_synthetic_control(
    df: pd.DataFrame,
    *,
    unit_col: str,
    period_col: str,
    outcome_col: str,
    treated_unit: Any,
    treat_period: int,
) -> dict[str, Any]:
    duplicate_count = int(df.duplicated(subset=[unit_col, period_col]).sum())
    if duplicate_count:
        raise ValueError(
            f"Synthetic control requires one row per (unit, period); "
            f"found {duplicate_count} duplicate (unit, period) rows."
        )
    panel = df.pivot_table(index=period_col, columns=unit_col, values=outcome_col).sort_index()
    if panel.isna().any().any():
        missing = int(panel.isna().sum().sum())
        raise ValueError(
            f"Synthetic control requires a balanced panel; pivot has {missing} missing cells. "
            "Provide one row per (unit, period) before calling estimate_synthetic_control."
        )
    if treated_unit not in panel.columns:
        raise ValueError(f"treated_unit {treated_unit!r} not present in panel.")
    pre = panel.loc[panel.index < treat_period]
    post = panel.loc[panel.index >= treat_period]
    if pre.empty or post.empty:
        raise ValueError("treat_period must split the panel into non-empty pre and post windows.")
    donor_cols = [c for c in panel.columns if c != treated_unit]
    if not donor_cols:
        raise ValueError("Synthetic control requires at least one donor unit.")
    target_pre = pre[treated_unit].values
    donors_pre = pre[donor_cols].values
    weights, success = _solve_weights(target_pre, donors_pre)

    counterfactual_post = post[donor_cols].values @ weights
    actual_post = post[treated_unit].values
    effects = actual_post - counterfactual_post
    avg_effect = float(np.mean(effects))

    if len(effects) > 1:
        se = float(np.std(effects, ddof=1) / np.sqrt(len(effects)))
        ci_low = avg_effect - 1.96 * se
        ci_high = avg_effect + 1.96 * se
        ci_method = "post-period SE"
    else:
        # Single post-period: fall back to placebo (in-space) distribution for inference.
        placebo_effects = _placebo_distribution(
            panel, treated_unit=treated_unit, treat_period=treat_period, actual_effect=avg_effect
        )
        ci_low = float(np.quantile(placebo_effects, 0.025))
        ci_high = float(np.quantile(placebo_effects, 0.975))
        ci_method = "placebo permutation"

    pre_residuals = target_pre - donors_pre @ weights
    pre_mspe = float(np.mean(pre_residuals**2))
    # Scale-relative MSPE: divide by pre-period variance of the treated unit so the
    # threshold is meaningful regardless of the outcome's units (binary, revenue, etc.).
    pre_variance = float(np.var(target_pre, ddof=0)) if target_pre.size > 1 else 0.0
    relative_mspe = pre_mspe / pre_variance if pre_variance > 1e-12 else pre_mspe
    solver_status = "passed" if success else "warning"
    diagnostics = {
        "pre_period_mspe": {
            "status": "passed" if relative_mspe < 0.05 else "warning",
            "details": (
                f"Pre-period MSPE = {pre_mspe:.5f} (relative to pre-period variance "
                f"= {relative_mspe:.3f})"
            ),
        },
        "donor_weights": {
            "status": "passed",
            "details": (
                "Weights: "
                + ", ".join(f"{c}={w:.2f}" for c, w in zip(donor_cols, weights, strict=False))
                + f"; sum={float(weights.sum()):.3f}"
            ),
        },
        "solver_status": {
            "status": solver_status,
            "details": (
                "SLSQP converged."
                if success
                else "SLSQP did not converge; treat result as suggestive."
            ),
        },
    }

    confidence = "medium" if (relative_mspe < 0.25 and success) else "low"
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
        "confidence_level": confidence,
        "diagnostics": diagnostics,
        "interpretation": (
            f"Synthetic control ATT = {avg_effect:+.4f} (95% CI "
            f"[{ci_low:+.4f}, {ci_high:+.4f}], {ci_method}); pre-period MSPE = {pre_mspe:.5f}."
        ),
    }
