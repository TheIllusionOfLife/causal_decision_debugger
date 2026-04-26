"""Covariate balance via standardized mean differences."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_THRESHOLD = 0.1


def _smd_numeric(series: pd.Series, treated_mask: pd.Series) -> float:
    a = series[treated_mask].astype(float)
    b = series[~treated_mask].astype(float)
    if a.empty or b.empty:
        return float("nan")
    var_a = float(a.var(ddof=0))
    var_b = float(b.var(ddof=0))
    pooled = math.sqrt((var_a + var_b) / 2.0) if (var_a + var_b) > 0 else 1e-12
    return abs(float(a.mean() - b.mean())) / pooled


def _smd_categorical(series: pd.Series, treated_mask: pd.Series) -> float:
    treated = series[treated_mask]
    control = series[~treated_mask]
    if treated.empty or control.empty:
        return float("nan")
    categories = sorted(set(series.dropna().unique()))
    smd_per_cat = []
    for cat in categories:
        p1 = float((treated == cat).mean())
        p0 = float((control == cat).mean())
        pooled = math.sqrt((p1 * (1 - p1) + p0 * (1 - p0)) / 2.0) if (p1 or p0) else 1e-12
        smd_per_cat.append(abs(p1 - p0) / max(pooled, 1e-12))
    return max(smd_per_cat) if smd_per_cat else 0.0


def _covariate_summary(df: pd.DataFrame, col: str, treated_mask: pd.Series) -> dict[str, Any]:
    series = df[col]
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        smd = _smd_numeric(series, treated_mask)
        return {
            "kind": "numeric",
            "smd": float(smd),
            "treated_mean": float(series[treated_mask].mean()),
            "control_mean": float(series[~treated_mask].mean()),
        }
    smd = _smd_categorical(series, treated_mask)
    return {
        "kind": "categorical",
        "smd": float(smd),
    }


def check_balance(
    df: pd.DataFrame,
    *,
    treatment_col: str,
    covariates: Iterable[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    treated_mask = df[treatment_col].astype(bool)
    summaries = {col: _covariate_summary(df, col, treated_mask) for col in covariates}
    failures = [c for c, s in summaries.items() if s["smd"] > threshold]
    overall = "failed" if failures else "passed"
    return {
        "overall_status": overall,
        "threshold": threshold,
        "treatment_col": treatment_col,
        "treated_n": int(treated_mask.sum()),
        "control_n": int((~treated_mask).sum()),
        "covariates": summaries,
        "failures": failures,
    }


def _read(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suffix in (".csv", ".tsv"):
        sep = "\t" if suffix == ".tsv" else ","
        return pd.read_csv(path, sep=sep)
    raise ValueError(f"unsupported file type: {suffix}")


def check_balance_file(
    path: Path,
    *,
    treatment_col: str,
    covariates: Iterable[str],
    threshold: float = DEFAULT_THRESHOLD,
    out_path: Path | None = None,
) -> dict[str, Any]:
    df = _read(Path(path))
    payload = check_balance(
        df, treatment_col=treatment_col, covariates=list(covariates), threshold=threshold
    )
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--treatment", required=True)
    parser.add_argument(
        "--covariates",
        required=True,
        help="Comma-separated covariate column names.",
    )
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    covariates = [c.strip() for c in args.covariates.split(",") if c.strip()]
    payload = check_balance_file(
        args.path.resolve(),
        treatment_col=args.treatment,
        covariates=covariates,
        threshold=args.threshold,
        out_path=args.out.resolve() if args.out else None,
    )
    if args.out is None:
        print(json.dumps(payload, indent=2))
    return 0 if payload["overall_status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
