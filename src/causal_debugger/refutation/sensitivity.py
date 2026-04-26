"""Sensitivity to unobserved confounding via the E-value."""

from __future__ import annotations

import math
from typing import Any


def e_value(risk_ratio: float) -> float:
    """E-value (VanderWeele & Ding, 2017) for a risk-ratio-style estimate.

    Inputs are clipped so the function returns a finite number for any positive RR.
    """
    rr = max(risk_ratio, 1e-9)
    if rr >= 1.0:
        return float(rr + math.sqrt(rr * (rr - 1.0)))
    inv = 1.0 / rr
    return float(inv + math.sqrt(inv * (inv - 1.0)))


def _approximate_risk_ratio(
    effect: float, baseline_outcome_rate: float
) -> float:
    p0 = max(min(baseline_outcome_rate, 0.999), 1e-3)
    p1 = max(min(p0 + effect, 0.999), 1e-3)
    return p1 / p0


def sensitivity_check(
    *,
    main_estimate: float,
    ci_low: float,
    ci_high: float,
    baseline_outcome_rate: float,
) -> dict[str, Any]:
    rr_point = _approximate_risk_ratio(main_estimate, baseline_outcome_rate)
    rr_bound = _approximate_risk_ratio(
        ci_low if main_estimate >= 0 else ci_high, baseline_outcome_rate
    )
    e_point = e_value(rr_point)
    e_bound = e_value(rr_bound)

    if e_bound < 1.25:
        status = "failed"
    elif e_bound < 1.75:
        status = "warning"
    else:
        status = "passed"

    return {
        "name": "sensitivity_to_unobserved_confounding",
        "status": status,
        "details": (
            f"E-value at point estimate ≈ {e_point:.2f}; at CI bound ≈ {e_bound:.2f}. "
            "Higher E-values mean stronger confounding is needed to explain the effect away."
        ),
        "delta_vs_main_estimate": None,
    }
