"""Sanity checks for synthetic DGPs: shapes, determinism, naive-vs-truth signals."""

from __future__ import annotations

import numpy as np
import pytest

from causal_debugger.scenarios.dgps import SCENARIOS


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_dgp_returns_nonempty(name: str) -> None:
    scen = SCENARIOS[name]()
    assert len(scen.frame) > 0
    assert "expected_status" in scen.truth


def test_randomized_ab_naive_recovers_ate() -> None:
    scen = SCENARIOS["randomized_ab"]()
    df = scen.frame
    naive = df[df.treated == 1].outcome.mean() - df[df.treated == 0].outcome.mean()
    assert abs(naive - scen.truth["true_ate"]) < 0.01


def test_observational_confounding_biases_naive_estimate() -> None:
    scen = SCENARIOS["observational_confounding"]()
    df = scen.frame
    naive = df[df.treated == 1].outcome.mean() - df[df.treated == 0].outcome.mean()
    assert naive - scen.truth["true_ate"] > 0.02, "Naive estimate should be biased upward"


def test_no_control_has_only_treated() -> None:
    scen = SCENARIOS["no_control"]()
    assert scen.frame.treated.unique().tolist() == [1]
    assert scen.truth["expected_status"] == "not_identifiable"


def test_dgps_are_deterministic() -> None:
    a = SCENARIOS["randomized_ab"]().frame.outcome.values
    b = SCENARIOS["randomized_ab"]().frame.outcome.values
    np.testing.assert_array_equal(a, b)
