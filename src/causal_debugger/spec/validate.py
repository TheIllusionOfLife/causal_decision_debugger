"""Spec validation: JSON-schema check + cross-field rules."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from causal_debugger.schemas import load_schema

KNOWN_METHODS = frozenset(
    {
        "ab_test",
        "ab_test_analysis",
        "regression_adjustment",
        "cuped",
        "difference_in_differences",
        "interrupted_time_series",
        "synthetic_control",
        "propensity_score_weighting",
        "matching",
        "doubly_robust_estimation",
        "cate",
        "causal_forest",
        "instrumental_variables",
        "regression_discontinuity",
        "not_identifiable",
    }
)


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str


def _schema_errors(spec: dict[str, Any]) -> list[ValidationError]:
    validator = Draft202012Validator(load_schema("causal_spec"))
    out: list[ValidationError] = []
    for err in validator.iter_errors(spec):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        out.append(ValidationError(path=path, message=err.message))
    return out


def _cross_field_errors(spec: dict[str, Any]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    variables = spec.get("variables") or {}
    pre = set(variables.get("pre_treatment_covariates") or [])
    forbidden = set(variables.get("forbidden_post_treatment_variables") or [])
    for shared in sorted(pre & forbidden):
        errors.append(
            ValidationError(
                path="variables.pre_treatment_covariates",
                message=(
                    f"{shared!r} is listed as a pre_treatment_covariate but also marked "
                    "as a forbidden post_treatment variable; cannot be used as a control."
                ),
            )
        )

    methods = spec.get("methods") or {}
    primary = methods.get("primary")
    if primary and primary not in KNOWN_METHODS:
        errors.append(
            ValidationError(
                path="methods.primary",
                message=f"unknown primary method: {primary!r}",
            )
        )

    for method in methods.get("secondary") or []:
        if method not in KNOWN_METHODS:
            errors.append(
                ValidationError(
                    path="methods.secondary",
                    message=f"unknown secondary method: {method!r}",
                )
            )

    return errors


def validate_spec(spec: dict[str, Any]) -> list[ValidationError]:
    errors = _schema_errors(spec)
    if not errors:
        errors.extend(_cross_field_errors(spec))
    return errors


def validate_spec_file(path: Path) -> list[ValidationError]:
    text = Path(path).read_text(encoding="utf-8")
    spec = yaml.safe_load(text)
    if not isinstance(spec, dict):
        raise yaml.YAMLError(f"spec at {path} did not parse to a mapping")
    return validate_spec(spec)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a causal_spec.yaml file.")
    parser.add_argument("path", type=Path, help="Path to causal_spec.yaml")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable text.",
    )
    args = parser.parse_args(argv)
    args.path = args.path.resolve()
    errors = validate_spec_file(args.path)
    if args.json:
        payload = {"valid": not errors, "errors": [asdict(e) for e in errors]}
        print(json.dumps(payload, indent=2))
    else:
        if not errors:
            print(f"OK: {args.path}")
        else:
            print(f"INVALID: {args.path}")
            for err in errors:
                print(f"  - [{err.path}] {err.message}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
