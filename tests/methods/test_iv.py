from __future__ import annotations

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator

from causal_debugger.methods.iv import estimate_iv
from causal_debugger.schemas import load_schema


def _encouragement(seed: int = 0, n: int = 20_000, true_late: float = 0.05) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    z = rng.binomial(1, 0.5, n)  # encouragement / instrument
    u = rng.normal(0, 1, n)  # unobserved confounder
    p_treat = 0.2 + 0.5 * z + 0.1 * u
    treated = (rng.uniform(size=n) < np.clip(p_treat, 0, 1)).astype(int)
    y = 0.3 + true_late * treated + 0.05 * u + rng.normal(0, 0.05, n)
    return pd.DataFrame({"instrument": z, "treated": treated, "outcome": y})


def test_iv_recovers_late() -> None:
    df = _encouragement()
    out = estimate_iv(df, treatment="treated", outcome="outcome", instrument="instrument")
    Draft202012Validator(load_schema("estimate_result")).validate(out)
    assert abs(out["effect_size"] - 0.05) < 0.02
    assert out["estimand"] == "LATE"


def test_iv_reports_first_stage_strength() -> None:
    df = _encouragement()
    out = estimate_iv(df, treatment="treated", outcome="outcome", instrument="instrument")
    assert "first_stage_F" in out["diagnostics"]
