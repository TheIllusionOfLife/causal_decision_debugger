"""Tests for the method router."""

from __future__ import annotations

from causal_debugger.methods.router import RouterContext, context_from_spec, suggest_method


def _ctx(**overrides) -> RouterContext:
    base = dict(
        randomized=False,
        has_pre_period=False,
        rollout_pattern="single",
        threshold_assignment=False,
        has_donor_pool=False,
        has_instrument=False,
        has_pre_treatment_covariates=True,
        has_comparison_group=True,
        heterogeneous_effect_question=False,
        sample_size=20_000,
        pre_treatment_covariate_count=4,
    )
    base.update(overrides)
    return RouterContext(**base)


def test_randomized_routes_to_ab() -> None:
    plan = suggest_method(_ctx(randomized=True))
    assert plan["primary_method"] == "ab_test_analysis"
    assert plan["identifiability_status"] == "identifiable"


def test_staggered_rollout_routes_to_did() -> None:
    plan = suggest_method(_ctx(rollout_pattern="staggered", has_pre_period=True))
    assert plan["primary_method"] == "difference_in_differences"


def test_threshold_routes_to_rdd() -> None:
    plan = suggest_method(_ctx(threshold_assignment=True))
    assert plan["primary_method"] == "regression_discontinuity"


def test_no_control_routes_to_not_identifiable() -> None:
    plan = suggest_method(_ctx(has_comparison_group=False))
    assert plan["primary_method"] == "not_identifiable"
    assert plan["identifiability_status"] == "not_identifiable"


def test_donor_pool_routes_to_synthetic_control() -> None:
    plan = suggest_method(
        _ctx(rollout_pattern="single_unit", has_donor_pool=True, has_pre_period=True)
    )
    assert plan["primary_method"] == "synthetic_control"


def test_observational_with_covariates_routes_to_dr() -> None:
    plan = suggest_method(_ctx())
    assert plan["primary_method"] == "doubly_robust_estimation"
    assert plan["identifiability_status"] == "weakly_identifiable"
    assert "propensity_score_weighting" in plan["secondary_methods"]


def test_heterogeneous_effects_adds_cate_secondary() -> None:
    plan = suggest_method(_ctx(heterogeneous_effect_question=True))
    assert "cate" in plan["secondary_methods"]


def test_instrument_routes_to_iv() -> None:
    plan = suggest_method(_ctx(has_instrument=True))
    assert plan["primary_method"] == "instrumental_variables"


def test_pure_time_series_routes_to_its() -> None:
    plan = suggest_method(
        _ctx(
            rollout_pattern="aggregate_time_series",
            has_pre_period=True,
            has_comparison_group=False,
            has_pre_treatment_covariates=False,
        )
    )
    assert plan["primary_method"] == "interrupted_time_series"


def test_plan_always_includes_required_keys() -> None:
    plan = suggest_method(_ctx())
    for key in (
        "primary_method",
        "secondary_methods",
        "required_assumptions",
        "diagnostics",
        "refutation_tests",
        "identifiability_status",
        "reasoning_summary",
    ):
        assert key in plan


def _spec(**overrides):
    base = {
        "causal_question": {"comparison_group": "eligible non-exposed users"},
        "variables": {"pre_treatment_covariates": ["country"]},
        "methods": {"primary": "doubly_robust_estimation"},
    }
    base.update(overrides)
    return base


def test_context_from_spec_derives_randomized_from_primary() -> None:
    ctx = context_from_spec(_spec(methods={"primary": "ab_test_analysis"}))
    assert ctx.randomized is True


def test_context_from_spec_derives_instrument_from_primary() -> None:
    ctx = context_from_spec(_spec(methods={"primary": "instrumental_variables"}))
    assert ctx.has_instrument is True


def test_context_from_spec_derives_threshold_from_primary() -> None:
    ctx = context_from_spec(_spec(methods={"primary": "regression_discontinuity"}))
    assert ctx.threshold_assignment is True


def test_context_from_spec_derives_did_from_primary() -> None:
    ctx = context_from_spec(_spec(methods={"primary": "difference_in_differences"}))
    assert ctx.has_pre_period is True
    assert ctx.rollout_pattern == "staggered"


def test_context_from_spec_design_block_overrides_primary() -> None:
    ctx = context_from_spec(
        _spec(
            methods={"primary": "ab_test_analysis"},
            design={"randomized": False, "has_instrument": True},
        )
    )
    assert ctx.randomized is False
    assert ctx.has_instrument is True
