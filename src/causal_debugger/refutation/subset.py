"""Subset stability: re-estimate per segment and compare to the main estimate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


def subset_stability(
    df: pd.DataFrame,
    *,
    segment_col: str,
    estimator: Callable[[pd.DataFrame], float],
    main_estimate: float,
    tolerance: float = 0.02,
) -> dict[str, Any]:
    per_segment: dict[Any, float] = {}
    for value, sub in df.groupby(segment_col):
        if len(sub) < 50:
            continue
        try:
            per_segment[value] = float(estimator(sub))
        except Exception:  # noqa: BLE001
            continue
    if not per_segment:
        return {
            "name": "subset_stability",
            "status": "warning",
            "details": "No segment had enough data to re-estimate.",
            "delta_vs_main_estimate": None,
        }
    deltas = {k: v - main_estimate for k, v in per_segment.items()}
    max_delta = max(abs(d) for d in deltas.values())
    if max_delta > 2 * tolerance:
        status = "failed"
    elif max_delta > tolerance:
        status = "warning"
    else:
        status = "passed"
    detail = ", ".join(f"{k}: {v:+.4f}" for k, v in per_segment.items())
    return {
        "name": "subset_stability",
        "status": status,
        "details": f"Per-segment estimates: {detail}; max |Δ vs main| = {max_delta:.4f}",
        "delta_vs_main_estimate": float(max_delta),
    }
