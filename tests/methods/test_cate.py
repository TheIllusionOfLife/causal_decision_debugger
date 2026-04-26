from __future__ import annotations

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator

from causal_debugger.methods.cate import estimate_cate
from causal_debugger.schemas import load_schema


def _heterogeneous(seed: int = 0, n: int = 5_000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    segment = rng.binomial(1, 0.5, n)
    treated = rng.binomial(1, 0.5, n)
    base = rng.normal(0.3, 0.05, n)
    effect_by_segment = np.where(segment == 1, 0.10, 0.02)
    p = np.clip(base + effect_by_segment * treated, 0.01, 0.99)
    outcome = rng.binomial(1, p)
    return pd.DataFrame(
        {
            "treated": treated,
            "outcome": outcome,
            "segment": segment,
            "covariate": rng.normal(0, 1, n),
        }
    )


def test_cate_returns_segment_effects() -> None:
    df = _heterogeneous()
    out = estimate_cate(
        df,
        treatment="treated",
        outcome="outcome",
        covariates=["segment", "covariate"],
    )
    Draft202012Validator(load_schema("estimate_result")).validate(out)
    seg_effects = out["diagnostics"]["segment_effects"]["details"]
    assert "segment=1" in seg_effects and "segment=0" in seg_effects
