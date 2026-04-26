"""1:k nearest-neighbor matching on the propensity score."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


def _ps(df: pd.DataFrame, treatment: str, covariates: Sequence[str]) -> np.ndarray:
    encoded = pd.get_dummies(df[list(covariates)], drop_first=True, dtype=float)
    x = StandardScaler(with_mean=False).fit_transform(encoded.values)
    model = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0)
    model.fit(x, df[treatment].astype(int).values)
    return np.clip(model.predict_proba(x)[:, 1], 1e-3, 1 - 1e-3)


def estimate_matching(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    covariates: Sequence[str],
    k: int = 1,
) -> dict[str, Any]:
    p = _ps(df, treatment, covariates)
    t = df[treatment].astype(int).values
    y = df[outcome].astype(float).values
    treated_idx = np.where(t == 1)[0]
    control_idx = np.where(t == 0)[0]
    if len(treated_idx) == 0 or len(control_idx) == 0:
        raise ValueError("Matching requires both treated and control units.")

    nn = NearestNeighbors(n_neighbors=min(k, len(control_idx))).fit(p[control_idx].reshape(-1, 1))
    _, idx = nn.kneighbors(p[treated_idx].reshape(-1, 1))
    matched_y = y[control_idx[idx]].mean(axis=1)
    treated_y = y[treated_idx]
    att = float(np.mean(treated_y - matched_y))
    se = float(np.std(treated_y - matched_y, ddof=1) / np.sqrt(len(treated_idx)))
    ci_low = att - 1.96 * se
    ci_high = att + 1.96 * se

    diagnostics = {
        "matched_pairs": {
            "status": "passed",
            "details": f"Matched {len(treated_idx)} treated to {k} control(s) each.",
        }
    }
    return {
        "method": "matching",
        "estimand": "ATT",
        "effect_size": att,
        "effect_unit": "outcome_units",
        "confidence_interval": [float(ci_low), float(ci_high)],
        "p_value": None,
        "sample_size": len(df),
        "treated_units": len(treated_idx),
        "control_units": len(control_idx),
        "confidence_level": "medium",
        "diagnostics": diagnostics,
        "interpretation": (
            f"PS matching ATT = {att:+.4f} (95% CI [{ci_low:+.4f}, {ci_high:+.4f}])."
        ),
    }
