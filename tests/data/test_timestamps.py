"""Tests for treatment-before-outcome timestamp checks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from causal_debugger.data.timestamps import check_timestamps, check_timestamps_file


def _good() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": np.arange(5),
            "treatment_time": pd.to_datetime(["2026-03-01"] * 5),
            "outcome_time": pd.to_datetime(["2026-03-08"] * 5),
        }
    )


def test_clean_data_passes() -> None:
    out = check_timestamps(_good(), "treatment_time", "outcome_time")
    assert out["status"] == "passed"
    assert out["invalid_row_count"] == 0


def test_treatment_after_outcome_is_flagged() -> None:
    df = _good()
    df.loc[0, "outcome_time"] = pd.Timestamp("2026-02-25")
    out = check_timestamps(df, "treatment_time", "outcome_time")
    assert out["status"] == "failed"
    assert out["invalid_row_count"] == 1
    assert 0 in out["invalid_indices"]


def test_equal_timestamps_are_invalid() -> None:
    df = _good()
    df.loc[1, "outcome_time"] = df.loc[1, "treatment_time"]
    out = check_timestamps(df, "treatment_time", "outcome_time")
    assert out["invalid_row_count"] == 1


def test_null_timestamps_counted_separately() -> None:
    df = _good()
    df.loc[2, "treatment_time"] = pd.NaT
    out = check_timestamps(df, "treatment_time", "outcome_time")
    assert out["null_row_count"] == 1
    assert out["status"] == "warning"


def test_unit_id_column_returned_when_provided() -> None:
    df = _good()
    df.loc[0, "outcome_time"] = pd.Timestamp("2026-02-25")
    out = check_timestamps(df, "treatment_time", "outcome_time", unit_id_col="user_id")
    assert out["invalid_unit_ids"] == [0]


def test_check_timestamps_file_writes_json(tmp_path: Path) -> None:
    parquet_path = tmp_path / "ts.parquet"
    _good().to_parquet(parquet_path)
    out_path = tmp_path / "ts.json"
    check_timestamps_file(parquet_path, "treatment_time", "outcome_time", out_path=out_path)
    assert out_path.exists()
