"""Templates shipped under skills/causal-decision-debugger/templates/ must validate against their schemas."""

from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from causal_debugger.schemas import load_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "skills" / "causal-decision-debugger" / "templates"


def _load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_causal_spec_template_validates() -> None:
    spec = _load_yaml(TEMPLATES / "causal_spec.yaml")
    Draft202012Validator(load_schema("causal_spec")).validate(spec)


def test_assumption_ledger_template_validates() -> None:
    ledger = _load_yaml(TEMPLATES / "assumption_ledger.yaml")
    Draft202012Validator(load_schema("assumption_ledger")).validate(ledger)
