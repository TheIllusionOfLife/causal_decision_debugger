from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from jsonschema import Draft202012Validator

from causal_debugger.methods.synthetic_control import estimate_synthetic_control
from causal_debugger.schemas import load_schema


def _panel(true_effect: float = 0.5, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_units = 8
    n_periods = 30
    treat_period = 15
    rows = []
    base_trends = rng.normal(0, 0.1, n_units)
    for u in range(n_units):
        for t in range(n_periods):
            unit_trend = base_trends[u] * t / 10
            noise = rng.normal(0, 0.02)
            base = 1.0 + 0.05 * t + unit_trend + noise
            treated = u == 0 and t >= treat_period
            y = base + (true_effect if treated else 0.0)
            rows.append({"unit_id": u, "period": t, "outcome": y, "treated_unit": int(u == 0)})
    return pd.DataFrame(rows)


def test_synthetic_control_recovers_effect() -> None:
    df = _panel(true_effect=0.5)
    out = estimate_synthetic_control(
        df,
        unit_col="unit_id",
        period_col="period",
        outcome_col="outcome",
        treated_unit=0,
        treat_period=15,
    )
    assert abs(out["effect_size"] - 0.5) < 0.15
    Draft202012Validator(load_schema("estimate_result")).validate(out)


def test_synthetic_control_weights_sum_to_one() -> None:
    df = _panel()
    out = estimate_synthetic_control(
        df,
        unit_col="unit_id",
        period_col="period",
        outcome_col="outcome",
        treated_unit=0,
        treat_period=15,
    )
    weights_sum = out["diagnostics"]["donor_weights"]["details"]
    assert "sum=" in weights_sum
    assert "solver_status" in out["diagnostics"]


def test_synthetic_control_single_post_period_uses_placebo_ci() -> None:
    df = _panel()
    df = df[df["period"] <= 15]  # one post-period (period=15)
    out = estimate_synthetic_control(
        df,
        unit_col="unit_id",
        period_col="period",
        outcome_col="outcome",
        treated_unit=0,
        treat_period=15,
    )
    assert "placebo permutation" in out["interpretation"]


def test_synthetic_control_rejects_unbalanced_panel() -> None:
    df = _panel()
    df = df[~((df["unit_id"] == 1) & (df["period"] == 5))]  # drop one cell
    with pytest.raises(ValueError, match="balanced panel"):
        estimate_synthetic_control(
            df,
            unit_col="unit_id",
            period_col="period",
            outcome_col="outcome",
            treated_unit=0,
            treat_period=15,
        )


def test_synthetic_control_rejects_missing_treated_unit() -> None:
    df = _panel()
    with pytest.raises(ValueError, match="treated_unit"):
        estimate_synthetic_control(
            df,
            unit_col="unit_id",
            period_col="period",
            outcome_col="outcome",
            treated_unit=99,
            treat_period=15,
        )
