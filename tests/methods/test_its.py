from __future__ import annotations

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator

from causal_debugger.methods.its import estimate_its
from causal_debugger.schemas import load_schema


def _series(true_level_shift: float = 0.5, n_periods: int = 60, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n_periods)
    intervention = n_periods // 2
    post = (t >= intervention).astype(int)
    y = 1.0 + 0.01 * t + true_level_shift * post + rng.normal(0, 0.05, n_periods)
    return pd.DataFrame({"period": t, "post": post, "outcome": y})


def test_its_recovers_level_shift() -> None:
    df = _series(true_level_shift=0.5)
    out = estimate_its(df, period_col="period", post_col="post", outcome_col="outcome")
    assert abs(out["effect_size"] - 0.5) < 0.05
    Draft202012Validator(load_schema("estimate_result")).validate(out)


def test_its_no_effect_yields_small_estimate() -> None:
    df = _series(true_level_shift=0.0)
    out = estimate_its(df, period_col="period", post_col="post", outcome_col="outcome")
    assert abs(out["effect_size"]) < 0.05
