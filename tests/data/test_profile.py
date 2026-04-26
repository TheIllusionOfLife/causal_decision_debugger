"""Tests for profile_dataframe."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from causal_debugger.data.profile import profile_dataframe, profile_file


def _fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": np.arange(100),
            "treated": np.array([0, 1] * 50),
            "outcome": np.concatenate([np.ones(70), np.zeros(30)]),
            "country": ["US"] * 60 + ["BR"] * 40,
            "missing_col": [None if i % 5 == 0 else i for i in range(100)],
            "treatment_time": pd.to_datetime(["2026-03-01"] * 100),
        }
    )


def test_profile_returns_row_count() -> None:
    out = profile_dataframe(_fixture())
    assert out["row_count"] == 100


def test_profile_counts_missing() -> None:
    out = profile_dataframe(_fixture())
    assert out["columns"]["missing_col"]["missing"] == 20
    assert out["columns"]["country"]["missing"] == 0


def test_profile_reports_cardinality() -> None:
    out = profile_dataframe(_fixture())
    assert out["columns"]["country"]["cardinality"] == 2
    assert out["columns"]["user_id"]["cardinality"] == 100


def test_profile_numeric_summaries() -> None:
    out = profile_dataframe(_fixture())
    summary = out["columns"]["outcome"]["numeric_summary"]
    assert summary is not None
    assert summary["mean"] == 0.7


def test_profile_timestamp_range() -> None:
    out = profile_dataframe(_fixture())
    ts = out["columns"]["treatment_time"]["timestamp_range"]
    assert ts is not None
    assert ts["min"].startswith("2026-03-01")


def test_profile_file_writes_json(tmp_path: Path) -> None:
    parquet_path = tmp_path / "fixture.parquet"
    _fixture().to_parquet(parquet_path)
    out_path = tmp_path / "profile.json"
    profile_file(parquet_path, out_path)
    payload = json.loads(out_path.read_text())
    assert payload["row_count"] == 100
