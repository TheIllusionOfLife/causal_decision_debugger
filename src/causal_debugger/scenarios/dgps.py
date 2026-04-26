"""Synthetic data-generating processes for golden test scenarios.

Each DGP returns (frame, truth) where ``truth`` is a dict shaped like::

    {"true_ate": float | None, "expected_status": str, "notes": str}

The eight scenarios match the acceptance-thresholds table in the implementation plan.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    frame: pd.DataFrame
    truth: dict


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def randomized_ab(n: int = 20_000, true_ate: float = 0.020, seed: int = 0) -> Scenario:
    rng = _rng(seed)
    treated = rng.binomial(1, 0.5, n).astype(int)
    base = rng.normal(0.30, 0.05, n)
    outcome_prob = np.clip(base + true_ate * treated, 0.01, 0.99)
    outcome = rng.binomial(1, outcome_prob).astype(int)
    df = pd.DataFrame(
        {
            "user_id": np.arange(n),
            "treated": treated,
            "outcome": outcome,
            "country": rng.choice(["US", "BR", "JP", "DE"], n),
            "device_type": rng.choice(["ios", "android"], n),
            "acquisition_channel": rng.choice(["organic", "paid", "referral"], n),
            "treatment_time": pd.Timestamp("2026-03-01"),
            "outcome_time": pd.Timestamp("2026-03-08"),
        }
    )
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "identifiable",
            "notes": "Randomized assignment; AB analysis should recover ATE within tolerance.",
        },
    )


def observational_confounding(n: int = 50_000, true_ate: float = 0.020, seed: int = 1) -> Scenario:
    rng = _rng(seed)
    motivation = rng.normal(0, 1, n)
    paid_channel = rng.binomial(1, 0.4, n)
    logit_p = -0.5 + 1.0 * motivation + 0.6 * paid_channel
    p = 1 / (1 + np.exp(-logit_p))
    treated = rng.binomial(1, p).astype(int)
    base = 0.30 + 0.05 * motivation + 0.02 * paid_channel
    outcome_prob = np.clip(base + true_ate * treated, 0.01, 0.99)
    outcome = rng.binomial(1, outcome_prob).astype(int)
    df = pd.DataFrame(
        {
            "user_id": np.arange(n),
            "treated": treated,
            "outcome": outcome,
            "motivation_proxy": motivation,
            "paid_channel": paid_channel,
            "country": rng.choice(["US", "BR", "JP", "DE"], n),
            "device_type": rng.choice(["ios", "android"], n),
            "treatment_time": pd.Timestamp("2026-03-01"),
            "outcome_time": pd.Timestamp("2026-03-08"),
        }
    )
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "weakly_identifiable",
            "notes": "Confounded by motivation; naive OLS biased upward, IPW/DR recover ATE.",
        },
    )


def parallel_trends_did(
    n_units: int = 200, n_periods: int = 12, true_ate: float = 0.030, seed: int = 2
) -> Scenario:
    rng = _rng(seed)
    units = np.arange(n_units)
    periods = np.arange(n_periods)
    treat_period = n_periods // 2
    is_treated_unit = units < n_units // 2
    rows = []
    unit_fe = rng.normal(0, 0.05, n_units)
    period_fe = np.linspace(0, 0.02, n_periods)
    for u in units:
        for t in periods:
            post = t >= treat_period
            d = 1 if (is_treated_unit[u] and post) else 0
            y = 0.30 + unit_fe[u] + period_fe[t] + true_ate * d + rng.normal(0, 0.02)
            rows.append((u, t, int(is_treated_unit[u]), int(post), int(d), float(y)))
    df = pd.DataFrame(rows, columns=["unit_id", "period", "group", "post", "treated", "outcome"])
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "identifiable",
            "notes": "Parallel pre-trends; DiD recovers ATE.",
        },
    )


def violated_pretrends_did(
    n_units: int = 200, n_periods: int = 12, true_ate: float = 0.030, seed: int = 3
) -> Scenario:
    rng = _rng(seed)
    units = np.arange(n_units)
    periods = np.arange(n_periods)
    treat_period = n_periods // 2
    is_treated_unit = units < n_units // 2
    rows = []
    unit_fe = rng.normal(0, 0.05, n_units)
    base_period_trend = np.linspace(0, 0.02, n_periods)
    treated_period_drift = np.linspace(0, 0.05, n_periods)  # diverging pre-trend
    for u in units:
        for t in periods:
            post = t >= treat_period
            d = 1 if (is_treated_unit[u] and post) else 0
            extra = treated_period_drift[t] if is_treated_unit[u] else 0.0
            y = (
                0.30
                + unit_fe[u]
                + base_period_trend[t]
                + extra
                + true_ate * d
                + rng.normal(0, 0.02)
            )
            rows.append((u, t, int(is_treated_unit[u]), int(post), int(d), float(y)))
    df = pd.DataFrame(rows, columns=["unit_id", "period", "group", "post", "treated", "outcome"])
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "weakly_identifiable",
            "notes": "Pre-trends diverge; DiD must emit a warning.",
        },
    )


def no_control(n: int = 5_000, seed: int = 4) -> Scenario:
    rng = _rng(seed)
    df = pd.DataFrame(
        {
            "user_id": np.arange(n),
            "treated": np.ones(n, dtype=int),
            "outcome": rng.binomial(1, 0.32, n).astype(int),
            "country": rng.choice(["US", "BR"], n),
            "treatment_time": pd.Timestamp("2026-03-01"),
            "outcome_time": pd.Timestamp("2026-03-08"),
        }
    )
    return Scenario(
        df,
        {
            "true_ate": None,
            "expected_status": "not_identifiable",
            "notes": "Everyone treated; no comparison group. Pipeline must surface not_identifiable.",
        },
    )


def post_treatment_leakage(n: int = 10_000, true_ate: float = 0.020, seed: int = 5) -> Scenario:
    rng = _rng(seed)
    treated = rng.binomial(1, 0.5, n).astype(int)
    base = rng.normal(0.30, 0.05, n)
    outcome_prob = np.clip(base + true_ate * treated, 0.01, 0.99)
    outcome = rng.binomial(1, outcome_prob).astype(int)
    tutorial_completed = ((treated == 1) & (rng.random(n) < 0.7)).astype(int)
    df = pd.DataFrame(
        {
            "user_id": np.arange(n),
            "treated": treated,
            "outcome": outcome,
            "tutorial_completed": tutorial_completed,
            "country": rng.choice(["US", "BR"], n),
            "treatment_time": pd.Timestamp("2026-03-01"),
            "outcome_time": pd.Timestamp("2026-03-08"),
        }
    )
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "spec_invalid",
            "notes": "tutorial_completed is post-treatment; spec validator must reject if listed as covariate.",
        },
    )


def poor_overlap(n: int = 30_000, true_ate: float = 0.020, seed: int = 6) -> Scenario:
    rng = _rng(seed)
    paid_channel = rng.binomial(1, 0.5, n)
    logit_p = -3.5 + 7.0 * paid_channel  # near-deterministic
    p = 1 / (1 + np.exp(-logit_p))
    treated = rng.binomial(1, p).astype(int)
    base = rng.normal(0.30, 0.04, n)
    outcome_prob = np.clip(base + true_ate * treated + 0.04 * paid_channel, 0.01, 0.99)
    outcome = rng.binomial(1, outcome_prob).astype(int)
    df = pd.DataFrame(
        {
            "user_id": np.arange(n),
            "treated": treated,
            "outcome": outcome,
            "paid_channel": paid_channel,
            "treatment_time": pd.Timestamp("2026-03-01"),
            "outcome_time": pd.Timestamp("2026-03-08"),
        }
    )
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "weakly_identifiable",
            "notes": "Treatment near-deterministic in paid_channel; overlap is poor — IPW must warn.",
        },
    )


def simultaneous_launch(
    n_units: int = 200, n_periods: int = 12, true_ate: float = 0.020, seed: int = 7
) -> Scenario:
    rng = _rng(seed)
    units = np.arange(n_units)
    periods = np.arange(n_periods)
    treat_period = n_periods // 2
    is_treated_unit = units < n_units // 2
    extra_launch_effect = 0.03  # confounding event hits everyone post-period
    rows = []
    unit_fe = rng.normal(0, 0.05, n_units)
    period_fe = np.linspace(0, 0.02, n_periods)
    for u in units:
        for t in periods:
            post = t >= treat_period
            d = 1 if (is_treated_unit[u] and post) else 0
            extra = extra_launch_effect if post else 0.0
            y = 0.30 + unit_fe[u] + period_fe[t] + extra + true_ate * d + rng.normal(0, 0.02)
            rows.append((u, t, int(is_treated_unit[u]), int(post), int(d), float(y)))
    df = pd.DataFrame(rows, columns=["unit_id", "period", "group", "post", "treated", "outcome"])
    return Scenario(
        df,
        {
            "true_ate": true_ate,
            "expected_status": "weakly_identifiable",
            "notes": "Concurrent launch hits everyone; DiD survives but confidence must be downgraded.",
        },
    )


SCENARIOS = {
    "randomized_ab": randomized_ab,
    "observational_confounding": observational_confounding,
    "parallel_trends_did": parallel_trends_did,
    "violated_pretrends_did": violated_pretrends_did,
    "no_control": no_control,
    "post_treatment_leakage": post_treatment_leakage,
    "poor_overlap": poor_overlap,
    "simultaneous_launch": simultaneous_launch,
}
