"""Tests for covariate balance / SMD."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from causal_debugger.data.balance import check_balance, check_balance_file


def _balanced() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 5000
    return pd.DataFrame(
        {
            "treated": rng.binomial(1, 0.5, n),
            "age": rng.normal(30, 5, n),
            "country": rng.choice(["US", "BR", "JP"], n),
        }
    )


def _imbalanced() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    n = 5000
    treated = rng.binomial(1, 0.5, n)
    age = np.where(treated == 1, rng.normal(35, 5, n), rng.normal(25, 5, n))
    country = np.where(treated == 1, "US", "BR")
    return pd.DataFrame({"treated": treated, "age": age, "country": country})


def test_balanced_data_has_low_smd() -> None:
    out = check_balance(_balanced(), treatment_col="treated", covariates=["age", "country"])
    assert out["overall_status"] == "passed"
    for col in ("age", "country"):
        assert out["covariates"][col]["smd"] < 0.1


def test_imbalanced_data_flagged() -> None:
    out = check_balance(_imbalanced(), treatment_col="treated", covariates=["age", "country"])
    assert out["overall_status"] == "failed"
    assert out["covariates"]["age"]["smd"] > 0.5


def test_smd_for_known_means_matches_formula() -> None:
    df = pd.DataFrame(
        {
            "treated": [0] * 100 + [1] * 100,
            "x": list(np.zeros(100)) + list(np.ones(100)),
        }
    )
    out = check_balance(df, treatment_col="treated", covariates=["x"])
    smd = out["covariates"]["x"]["smd"]
    expected = (1.0 - 0.0) / math.sqrt((0.0 + 0.0) / 2 + 1e-12)
    # both groups have zero variance; the function should fall back to a finite value
    assert math.isfinite(smd)
    assert smd > expected / 1e6  # large


def test_check_balance_file_writes_json(tmp_path: Path) -> None:
    parquet_path = tmp_path / "bal.parquet"
    _balanced().to_parquet(parquet_path)
    out_path = tmp_path / "bal.json"
    check_balance_file(
        parquet_path,
        treatment_col="treated",
        covariates=["age", "country"],
        out_path=out_path,
    )
    assert out_path.exists()


def test_threshold_is_configurable() -> None:
    out = check_balance(
        _imbalanced(),
        treatment_col="treated",
        covariates=["age"],
        threshold=10.0,
    )
    assert out["overall_status"] == "passed"
