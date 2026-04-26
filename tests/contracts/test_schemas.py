"""Validate that artifact schemas accept canonical examples and reject malformed payloads.

Examples mirror the artifacts in causal_decision_debugger_build_spec.md §8.
"""

from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator

from causal_debugger.schemas import SCHEMA_NAMES, load_schema

CAUSAL_SPEC_EXAMPLE = {
    "analysis_id": "onboarding_retention_2026_03",
    "status": "draft",
    "created_by": "causal-decision-debugger",
    "business_decision": {
        "question": "Should we keep onboarding_v2?",
        "owner": "growth_team",
        "action_options": ["keep", "rollback", "run_followup_experiment"],
    },
    "causal_question": {
        "question": "What is the effect of onboarding_v2 exposure on D7 retention?",
        "unit": "user",
        "treatment": {
            "name": "onboarding_v2_exposed",
            "type": "binary",
            "treatment_time": "onboarding_started_at",
        },
        "outcome": {
            "name": "retained_d7",
            "type": "binary",
            "outcome_window": "signup_at + 7 days",
        },
        "comparison_group": "eligible users not exposed to onboarding_v2",
    },
    "population": {
        "eligibility_definition": "new users who signed up during rollout window",
        "inclusion_criteria": ["has signup timestamp", "eligible for onboarding experience"],
        "exclusion_criteria": ["internal test accounts", "users with missing signup timestamp"],
    },
    "data": {
        "warehouse": "local",
        "local_path": "examples/onboarding_retention/data/observational.parquet",
    },
    "variables": {
        "pre_treatment_covariates": [
            "country",
            "device_type",
            "acquisition_channel",
            "signup_week",
        ],
        "forbidden_post_treatment_variables": [
            "tutorial_completed",
            "first_purchase_after_signup",
            "session_count_after_treatment",
        ],
        "suspected_unobserved_confounders": ["user_motivation", "prior_brand_awareness"],
    },
    "assumptions": {
        "no_unobserved_confounding": {
            "status": "uncertain",
            "notes": "User motivation is not directly observed.",
        },
        "treatment_precedes_outcome": {"status": "confirmed"},
        "no_simultaneous_major_change": {"status": "unknown"},
        "positivity_overlap": {"status": "unknown"},
        "stable_unit_treatment_value": {"status": "plausible"},
    },
    "methods": {"primary": None, "secondary": [], "robustness": []},
}

ASSUMPTION_LEDGER_EXAMPLE = {
    "assumptions": [
        {
            "id": "A1",
            "name": "Treatment happened before outcome",
            "status": "confirmed",
            "importance": "critical",
            "evidence": "onboarding_started_at occurs before D7 retention window",
            "risk_if_false": "Analysis would contain time leakage",
            "how_to_check_or_improve": "Validate timestamp ordering for every user",
        },
        {
            "id": "A2",
            "name": "No major simultaneous change",
            "status": "unknown",
            "importance": "high",
            "evidence": "No rollout calendar has been checked yet",
            "risk_if_false": "Metric change may be caused by another launch",
            "how_to_check_or_improve": "Ask PM/engineer and inspect release logs",
        },
    ]
}

ESTIMATE_RESULT_EXAMPLE = {
    "method": "doubly_robust_estimation",
    "estimand": "ATE",
    "effect_size": 0.021,
    "effect_unit": "percentage_points",
    "confidence_interval": [0.008, 0.034],
    "p_value": 0.012,
    "sample_size": 128430,
    "treated_units": 42100,
    "control_units": 86330,
    "confidence_level": "medium",
    "diagnostics": {
        "covariate_balance": {
            "status": "passed",
            "details": "All standardized mean differences below 0.1 after weighting.",
        },
        "propensity_overlap": {
            "status": "warning",
            "details": "Poor overlap for paid acquisition users.",
        },
    },
    "interpretation": (
        "Under the stated assumptions, onboarding_v2 likely increased D7 retention by "
        "about 2.1 percentage points."
    ),
}

IDENTIFIABILITY_FAILURE_EXAMPLE = {
    "identifiability_status": "not_identifiable",
    "reasons": [
        "All users received the feature on the same day.",
        "No untreated comparison group exists.",
    ],
    "recommended_next_action": (
        "Create a 10% randomized holdout or use a staggered rollout in the next launch."
    ),
    "method_attempted": "difference_in_differences",
}

REFUTATION_RESULT_EXAMPLE = {
    "name": "placebo_outcome",
    "status": "passed",
    "details": "No significant effect on pre-treatment activity proxy.",
    "delta_vs_main_estimate": 0.001,
}

EXAMPLES = {
    "causal_spec": CAUSAL_SPEC_EXAMPLE,
    "assumption_ledger": ASSUMPTION_LEDGER_EXAMPLE,
    "estimate_result": ESTIMATE_RESULT_EXAMPLE,
    "identifiability_failure": IDENTIFIABILITY_FAILURE_EXAMPLE,
    "refutation_result": REFUTATION_RESULT_EXAMPLE,
}


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name))


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schemas_load(name: str) -> None:
    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_canonical_examples_validate(name: str) -> None:
    _validator(name).validate(EXAMPLES[name])


def test_causal_spec_rejects_bad_status() -> None:
    bad = copy.deepcopy(CAUSAL_SPEC_EXAMPLE)
    bad["status"] = "live"
    errors = list(_validator("causal_spec").iter_errors(bad))
    assert errors, "expected an error for invalid status enum"


def test_causal_spec_rejects_missing_required_field() -> None:
    bad = copy.deepcopy(CAUSAL_SPEC_EXAMPLE)
    del bad["business_decision"]
    errors = list(_validator("causal_spec").iter_errors(bad))
    assert errors, "expected required-field error"


def test_assumption_ledger_rejects_unknown_status() -> None:
    bad = copy.deepcopy(ASSUMPTION_LEDGER_EXAMPLE)
    bad["assumptions"][0]["status"] = "maybe"
    errors = list(_validator("assumption_ledger").iter_errors(bad))
    assert errors


def test_assumption_ledger_rejects_extra_top_level_key() -> None:
    bad = copy.deepcopy(ASSUMPTION_LEDGER_EXAMPLE)
    bad["notes"] = "extraneous"
    errors = list(_validator("assumption_ledger").iter_errors(bad))
    assert errors


def test_estimate_result_rejects_extra_field() -> None:
    bad = copy.deepcopy(ESTIMATE_RESULT_EXAMPLE)
    bad["surprise"] = 1
    errors = list(_validator("estimate_result").iter_errors(bad))
    assert errors


def test_estimate_result_rejects_bad_confidence_level() -> None:
    bad = copy.deepcopy(ESTIMATE_RESULT_EXAMPLE)
    bad["confidence_level"] = "very_high"
    errors = list(_validator("estimate_result").iter_errors(bad))
    assert errors


def test_estimate_result_rejects_short_ci() -> None:
    bad = copy.deepcopy(ESTIMATE_RESULT_EXAMPLE)
    bad["confidence_interval"] = [0.0]
    errors = list(_validator("estimate_result").iter_errors(bad))
    assert errors


def test_identifiability_failure_requires_const_status() -> None:
    bad = copy.deepcopy(IDENTIFIABILITY_FAILURE_EXAMPLE)
    bad["identifiability_status"] = "weakly_identifiable"
    errors = list(_validator("identifiability_failure").iter_errors(bad))
    assert errors


def test_refutation_result_rejects_bad_status() -> None:
    bad = copy.deepcopy(REFUTATION_RESULT_EXAMPLE)
    bad["status"] = "ok"
    errors = list(_validator("refutation_result").iter_errors(bad))
    assert errors


def test_load_schema_unknown_raises() -> None:
    with pytest.raises(ValueError):
        load_schema("not_a_schema")
