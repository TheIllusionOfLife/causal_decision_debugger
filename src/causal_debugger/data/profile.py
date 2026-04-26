"""Profile a dataframe: row count, missingness, cardinality, numeric/timestamp summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from causal_debugger.data.io import read_table


def _column_summary(series: pd.Series) -> dict[str, Any]:
    missing = int(series.isna().sum())
    cardinality = int(series.nunique(dropna=True))
    numeric_summary: dict[str, float] | None = None
    timestamp_range: dict[str, str] | None = None
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        clean = series.dropna()
        if not clean.empty:
            numeric_summary = {
                "mean": float(clean.mean()),
                "std": float(clean.std(ddof=0)),
                "min": float(clean.min()),
                "p25": float(clean.quantile(0.25)),
                "median": float(clean.median()),
                "p75": float(clean.quantile(0.75)),
                "max": float(clean.max()),
            }
    if pd.api.types.is_datetime64_any_dtype(series):
        clean = series.dropna()
        if not clean.empty:
            timestamp_range = {
                "min": clean.min().isoformat(),
                "max": clean.max().isoformat(),
            }
    return {
        "dtype": str(series.dtype),
        "missing": missing,
        "cardinality": cardinality,
        "numeric_summary": numeric_summary,
        "timestamp_range": timestamp_range,
    }


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "row_count": len(df),
        "column_count": int(df.shape[1]),
        "columns": {col: _column_summary(df[col]) for col in df.columns},
    }


def profile_file(path: Path, out_path: Path | None = None) -> dict[str, Any]:
    df = read_table(Path(path))
    payload = profile_dataframe(df)
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = profile_file(args.path.resolve(), args.out.resolve() if args.out else None)
    if args.out is None:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
