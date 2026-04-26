from __future__ import annotations

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator

from causal_debugger.methods.rdd import estimate_rdd
from causal_debugger.schemas import load_schema


def _threshold_data(true_jump: float = 0.4, seed: int = 0, n: int = 5_000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    score = rng.uniform(-1.0, 1.0, n)
    treated = (score >= 0).astype(int)
    y = 1.0 + 0.3 * score + true_jump * treated + rng.normal(0, 0.1, n)
    return pd.DataFrame({"running": score, "treated": treated, "outcome": y})


def test_rdd_recovers_jump() -> None:
    df = _threshold_data(true_jump=0.4)
    out = estimate_rdd(df, running_var="running", outcome="outcome", cutoff=0.0)
    Draft202012Validator(load_schema("estimate_result")).validate(out)
    assert abs(out["effect_size"] - 0.4) < 0.05


def test_rdd_diagnostics_include_bandwidth() -> None:
    df = _threshold_data()
    out = estimate_rdd(df, running_var="running", outcome="outcome", cutoff=0.0)
    assert "bandwidth_sensitivity" in out["diagnostics"]
