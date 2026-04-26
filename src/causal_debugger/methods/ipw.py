"""Propensity-score weighting estimator (Horvitz-Thompson + Hájek)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def _design_matrix(df: pd.DataFrame, covariates: Sequence[str]) -> np.ndarray:
    encoded = pd.get_dummies(df[list(covariates)], drop_first=True, dtype=float)
    return StandardScaler(with_mean=False).fit_transform(encoded.values)


def _propensity(df: pd.DataFrame, treatment: str, covariates: Sequence[str]) -> np.ndarray:
    x = _design_matrix(df, covariates)
    y = df[treatment].astype(int).values
    model = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0)
    model.fit(x, y)
    p = model.predict_proba(x)[:, 1]
    return np.clip(p, 1e-3, 1 - 1e-3)


def estimate_ipw(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    covariates: Sequence[str],
) -> dict[str, Any]:
    p = _propensity(df, treatment, covariates)
    t = df[treatment].astype(float).values
    y = df[outcome].astype(float).values
    w1 = t / p
    w0 = (1 - t) / (1 - p)
    # Hájek (stabilized) for robustness
    mu1 = float(np.sum(w1 * y) / max(np.sum(w1), 1e-9))
    mu0 = float(np.sum(w0 * y) / max(np.sum(w0), 1e-9))
    ate = mu1 - mu0
    n = len(df)
    influence = (t * (y - mu1) / p) - ((1 - t) * (y - mu0) / (1 - p))
    se = float(np.std(influence, ddof=1) / np.sqrt(n))
    ci_low = ate - 1.96 * se
    ci_high = ate + 1.96 * se

    overlap_violation = float(np.mean((p < 0.05) | (p > 0.95)))
    overlap_status = "warning" if overlap_violation > 0.05 else "passed"
    if overlap_violation > 0.25:
        overlap_status = "failed"
    diagnostics = {
        "propensity_overlap": {
            "status": overlap_status,
            "details": (f"Share of units with PS in [0,0.05] or [0.95,1]: {overlap_violation:.3f}"),
        }
    }
    confidence = "medium"
    if overlap_status != "passed":
        confidence = "low"

    return {
        "method": "propensity_score_weighting",
        "estimand": "ATE",
        "effect_size": ate,
        "effect_unit": "outcome_units",
        "confidence_interval": [float(ci_low), float(ci_high)],
        "p_value": None,
        "sample_size": int(n),
        "treated_units": int(t.sum()),
        "control_units": int((1 - t).sum()),
        "confidence_level": confidence,
        "diagnostics": diagnostics,
        "interpretation": (
            f"IPW (Hájek) ATE = {ate:+.4f} (95% CI [{ci_low:+.4f}, {ci_high:+.4f}])."
        ),
    }
