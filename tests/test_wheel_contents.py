"""Verify the built wheel ships everything the runtime needs.

The five JSON schemas under ``causal_debugger/schemas/`` are loaded at runtime
via ``importlib.resources``. If hatchling drops them from the wheel, every
estimator silently breaks the moment a user installs the package. Catch that at
build time, not in the field.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SCHEMAS = (
    "causal_debugger/schemas/causal_spec.schema.json",
    "causal_debugger/schemas/assumption_ledger.schema.json",
    "causal_debugger/schemas/estimate_result.schema.json",
    "causal_debugger/schemas/identifiability_failure.schema.json",
    "causal_debugger/schemas/refutation_result.schema.json",
)


def _have_uv() -> bool:
    return shutil.which("uv") is not None


@pytest.mark.skipif(not _have_uv(), reason="uv not installed in test env")
def test_wheel_includes_schemas(tmp_path: Path) -> None:
    out_dir = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    wheels = list(out_dir.glob("causal_debugger-*.whl"))
    assert len(wheels) == 1, f"expected 1 wheel, got {wheels}"

    with zipfile.ZipFile(wheels[0]) as zf:
        names = set(zf.namelist())

    missing = [s for s in EXPECTED_SCHEMAS if s not in names]
    assert not missing, f"wheel is missing schema files: {missing}"

    # Console script entry must be declared so `causal-debugger` becomes
    # available after install. This is what bootstrap.py greps for.
    entry_paths = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
    assert entry_paths, (
        f"wheel is missing .dist-info/entry_points.txt; without it the "
        f"`causal-debugger` console script never gets registered. names={sorted(names)}"
    )
    with zipfile.ZipFile(wheels[0]) as zf:
        entry_text = zf.read(entry_paths[0]).decode()
    assert "causal-debugger = causal_debugger.cli:main" in entry_text, entry_text
