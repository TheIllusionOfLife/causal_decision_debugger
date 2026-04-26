"""Doubly robust ATE via AIPW with K-fold cross-fitting."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler


def _design(df: pd.DataFrame, covariates: Sequence[str]) -> np.ndarray:
    encoded = pd.get_dummies(df[list(covariates)], drop_first=True, dtype=float)
    return StandardScaler(with_mean=False).fit_transform(encoded.values)


def _cross_fit_nuisances(
    x: np.ndarray, t: np.ndarray, y: np.ndarray, *, n_splits: int = 5, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(t)
    p = np.zeros(n)
    mu1 = np.zeros(n)
    mu0 = np.zeros(n)
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for train_idx, test_idx in kf.split(x):
        x_tr, x_te = x[train_idx], x[test_idx]
        t_tr = t[train_idx]
        y_tr = y[train_idx]
        ps = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0).fit(x_tr, t_tr)
        p[test_idx] = ps.predict_proba(x_te)[:, 1]
        treated = t_tr == 1
        control = t_tr == 0
        if treated.sum() >= 2:
            mu1[test_idx] = Ridge(alpha=1.0).fit(x_tr[treated], y_tr[treated]).predict(x_te)
        else:
            mu1[test_idx] = float(y_tr[treated].mean()) if treated.any() else float(y_tr.mean())
        if control.sum() >= 2:
            mu0[test_idx] = Ridge(alpha=1.0).fit(x_tr[control], y_tr[control]).predict(x_te)
        else:
            mu0[test_idx] = float(y_tr[control].mean()) if control.any() else float(y_tr.mean())
    return np.clip(p, 1e-3, 1 - 1e-3), mu1, mu0


def estimate_doubly_robust(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    covariates: Sequence[str],
) -> dict[str, Any]:
    x = _design(df, covariates)
    t = df[treatment].astype(int).values
    y = df[outcome].astype(float).values

    p, mu1, mu0 = _cross_fit_nuisances(x, t, y)

    aipw_per_unit = mu1 - mu0 + t * (y - mu1) / p - (1 - t) * (y - mu0) / (1 - p)
    ate = float(np.mean(aipw_per_unit))
    se = float(np.std(aipw_per_unit, ddof=1) / np.sqrt(len(df)))
    ci_low = ate - 1.96 * se
    ci_high = ate + 1.96 * se

    overlap_share = float(np.mean((p < 0.05) | (p > 0.95)))
    overlap_status = "warning" if overlap_share > 0.05 else "passed"
    if overlap_share > 0.25:
        overlap_status = "failed"
    diagnostics = {
        "propensity_overlap": {
            "status": overlap_status,
            "details": f"Share of units with PS in tails: {overlap_share:.3f}",
        }
    }
    confidence = "medium" if overlap_status == "passed" else "low"

    return {
        "method": "doubly_robust_estimation",
        "estimand": "ATE",
        "effect_size": ate,
        "effect_unit": "outcome_units",
        "confidence_interval": [float(ci_low), float(ci_high)],
        "p_value": None,
        "sample_size": len(df),
        "treated_units": int(t.sum()),
        "control_units": int((1 - t).sum()),
        "confidence_level": confidence,
        "diagnostics": diagnostics,
        "interpretation": (
            f"AIPW ATE = {ate:+.4f} (95% CI [{ci_low:+.4f}, {ci_high:+.4f}]) — "
            "doubly robust against propensity or outcome misspecification."
        ),
    }
