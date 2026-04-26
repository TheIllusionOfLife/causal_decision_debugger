"""Verify treatment_time precedes outcome_time."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from causal_debugger.data.io import read_table


def check_timestamps(
    df: pd.DataFrame,
    treatment_time_col: str,
    outcome_time_col: str,
    *,
    unit_id_col: str | None = None,
) -> dict[str, Any]:
    treat = pd.to_datetime(df[treatment_time_col], errors="coerce")
    outcome = pd.to_datetime(df[outcome_time_col], errors="coerce")
    null_mask = treat.isna() | outcome.isna()
    invalid_mask = (~null_mask) & (outcome <= treat)

    invalid_indices = df.index[invalid_mask].tolist()
    invalid_unit_ids: list[Any] = []
    if unit_id_col is not None:
        invalid_unit_ids = df.loc[invalid_mask, unit_id_col].tolist()

    null_count = int(null_mask.sum())
    invalid_count = int(invalid_mask.sum())
    if invalid_count > 0:
        status = "failed"
    elif null_count > 0:
        status = "warning"
    else:
        status = "passed"

    return {
        "status": status,
        "treatment_time_col": treatment_time_col,
        "outcome_time_col": outcome_time_col,
        "row_count": len(df),
        "invalid_row_count": invalid_count,
        "null_row_count": null_count,
        "invalid_indices": [int(i) for i in invalid_indices],
        "invalid_unit_ids": invalid_unit_ids,
    }


def check_timestamps_file(
    path: Path,
    treatment_time_col: str,
    outcome_time_col: str,
    *,
    unit_id_col: str | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    df = read_table(Path(path), parse_dates=True)
    payload = check_timestamps(df, treatment_time_col, outcome_time_col, unit_id_col=unit_id_col)
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, default=str))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--treatment-time", required=True)
    parser.add_argument("--outcome-time", required=True)
    parser.add_argument("--unit-id", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = check_timestamps_file(
        args.path.resolve(),
        args.treatment_time,
        args.outcome_time,
        unit_id_col=args.unit_id,
        out_path=args.out.resolve() if args.out else None,
    )
    if args.out is None:
        print(json.dumps(payload, indent=2, default=str))
    return 0 if payload["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
