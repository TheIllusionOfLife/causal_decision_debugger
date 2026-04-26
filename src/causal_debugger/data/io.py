"""Tiny tabular file reader shared across data scripts and the pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path: Path, *, parse_dates: bool = False) -> pd.DataFrame:
    """Read a parquet/csv/tsv file into a DataFrame.

    Args:
        path: file to read
        parse_dates: forwarded to ``pd.read_csv`` for csv/tsv inputs

    Raises:
        ValueError: if the file extension is not recognized.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suffix in (".csv", ".tsv"):
        sep = "\t" if suffix == ".tsv" else ","
        return pd.read_csv(path, sep=sep, parse_dates=parse_dates)
    raise ValueError(f"unsupported file type: {suffix}")
