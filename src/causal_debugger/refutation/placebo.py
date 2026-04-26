"""Placebo refutations: shuffle treatment, expect a near-null effect."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def placebo_treatment_test(
    df: pd.DataFrame,
    *,
    treatment: str,
    outcome: str,
    main_estimate: float,
    threshold: float = 0.01,
    seed: int = 0,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(df[treatment].values)
    treat_y = df.loc[shuffled == 1, outcome].astype(float)
    control_y = df.loc[shuffled == 0, outcome].astype(float)
    placebo_effect = float(treat_y.mean() - control_y.mean())
    delta = placebo_effect  # vs zero, since true effect should be ~0 under shuffled treatment
    if abs(placebo_effect) > max(threshold, abs(main_estimate) * 0.25):
        status = "warning"
    else:
        status = "passed"
    if abs(placebo_effect) > max(threshold, abs(main_estimate) * 0.5):
        status = "failed"
    return {
        "name": "placebo_treatment",
        "status": status,
        "details": (
            f"Shuffled treatment yields effect {placebo_effect:+.4f}; "
            f"main estimate is {main_estimate:+.4f}."
        ),
        "delta_vs_main_estimate": float(delta - main_estimate),
    }


def placebo_outcome_test(
    df: pd.DataFrame,
    *,
    treatment: str,
    placebo_outcome: str,
    main_estimate: float,
    threshold: float = 0.01,
) -> dict[str, Any]:
    treat_y = df.loc[df[treatment] == 1, placebo_outcome].astype(float)
    control_y = df.loc[df[treatment] == 0, placebo_outcome].astype(float)
    effect = float(treat_y.mean() - control_y.mean())
    status = "passed" if abs(effect) <= threshold else "warning"
    if abs(effect) > max(threshold, abs(main_estimate) * 0.5):
        status = "failed"
    return {
        "name": "placebo_outcome",
        "status": status,
        "details": (
            f"Effect on placebo outcome '{placebo_outcome}' = {effect:+.4f}; should be near zero."
        ),
        "delta_vs_main_estimate": float(effect - main_estimate),
    }
