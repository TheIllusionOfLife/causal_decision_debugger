"""Doubly robust ATE via AIPW (sklearn nuisance models, no econml dependency for the core path)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler


def _design(df: pd.DataFrame, covariates: Sequence[str]) -> np.ndarray:
    encoded = pd.get_dummies(df[list(covariates)], drop_first=True, dtype=float)
    return StandardScaler(with_mean=False).fit_transform(encoded.values)


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

    ps_model = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0)
    ps_model.fit(x, t)
    p = np.clip(ps_model.predict_proba(x)[:, 1], 1e-3, 1 - 1e-3)

    mu1 = Ridge(alpha=1.0).fit(x[t == 1], y[t == 1]).predict(x)
    mu0 = Ridge(alpha=1.0).fit(x[t == 0], y[t == 0]).predict(x)

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
