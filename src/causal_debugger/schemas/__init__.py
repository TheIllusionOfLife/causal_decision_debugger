"""JSON schemas for causal-debugger artifacts."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

SCHEMA_NAMES = (
    "causal_spec",
    "assumption_ledger",
    "estimate_result",
    "identifiability_failure",
    "refutation_result",
)


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Load a JSON schema by short name (e.g. ``"causal_spec"``)."""
    if name not in SCHEMA_NAMES:
        raise ValueError(f"unknown schema: {name!r} (known: {SCHEMA_NAMES})")
    resource = resources.files(__package__).joinpath(f"{name}.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


__all__ = ["SCHEMA_NAMES", "load_schema"]
