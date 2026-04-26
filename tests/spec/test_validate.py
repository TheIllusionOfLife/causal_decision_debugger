"""TDD tests for spec validation: schema + cross-field rules."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from causal_debugger.spec.validate import ValidationError, validate_spec, validate_spec_file

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SPEC = REPO_ROOT / "examples" / "onboarding_retention" / "causal_spec.yaml"


def _load_example() -> dict:
    return yaml.safe_load(EXAMPLE_SPEC.read_text(encoding="utf-8"))


def test_example_spec_validates() -> None:
    errors = validate_spec(_load_example())
    assert errors == []


def test_example_spec_file_validates() -> None:
    errors = validate_spec_file(EXAMPLE_SPEC)
    assert errors == []


def test_missing_required_field_reports_error() -> None:
    spec = _load_example()
    del spec["business_decision"]
    errors = validate_spec(spec)
    assert any("business_decision" in e.message for e in errors)


def test_post_treatment_variable_in_covariates_is_rejected() -> None:
    spec = _load_example()
    spec["variables"]["pre_treatment_covariates"].append("tutorial_completed")
    errors = validate_spec(spec)
    assert any(
        "tutorial_completed" in e.message and "post_treatment" in e.message for e in errors
    )


def test_invalid_status_enum_is_rejected() -> None:
    spec = _load_example()
    spec["status"] = "live"
    errors = validate_spec(spec)
    assert any(e.path == "status" for e in errors)


def test_unknown_assumption_status_is_rejected() -> None:
    spec = _load_example()
    spec["assumptions"]["custom_assumption"] = {"status": "definitely"}
    errors = validate_spec(spec)
    assert any("definitely" in e.message or "custom_assumption" in e.message for e in errors)


def test_unknown_primary_method_is_rejected() -> None:
    spec = _load_example()
    spec["methods"]["primary"] = "magic_method"
    errors = validate_spec(spec)
    assert any("magic_method" in e.message for e in errors)


def test_validation_error_dataclass_fields() -> None:
    spec = _load_example()
    spec["status"] = "live"
    errors = validate_spec(spec)
    assert all(isinstance(e, ValidationError) for e in errors)
    assert all(e.path and e.message for e in errors)


def test_pre_treatment_and_forbidden_overlap_emits_one_error_per_var() -> None:
    spec = _load_example()
    spec["variables"]["pre_treatment_covariates"].extend(
        ["tutorial_completed", "first_purchase_after_signup"]
    )
    errors = validate_spec(spec)
    flagged = [e for e in errors if "post_treatment" in e.message]
    assert len(flagged) == 2


def test_validate_spec_file_missing_path_raises() -> None:
    with pytest.raises(FileNotFoundError):
        validate_spec_file(Path("/no/such/spec.yaml"))


def test_validate_spec_file_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("::: not yaml :::")
    with pytest.raises(yaml.YAMLError):
        validate_spec_file(bad)


def test_extra_fields_are_allowed() -> None:
    spec = _load_example()
    spec["custom_metadata"] = {"owner": "growth"}
    errors = validate_spec(spec)
    assert errors == []


def test_status_completed_is_valid() -> None:
    spec = copy.deepcopy(_load_example())
    spec["status"] = "completed"
    assert validate_spec(spec) == []
