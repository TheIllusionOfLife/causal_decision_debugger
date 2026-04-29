"""Tests for the shared `_install_paths` helper.

The helper is imported by both `bootstrap.py` and `bin/causal-debugger`. They
must agree on where the venv lives, so this is the single source of truth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = REPO_ROOT / "skills" / "diagnose" / "scripts" / "_install_paths.py"


def _load_helper():
    spec = importlib.util.spec_from_file_location("_install_paths", HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def helper():
    return _load_helper()


def test_resolves_from_env_var(helper, tmp_path: Path) -> None:
    env = {"CLAUDE_PLUGIN_DATA": str(tmp_path)}
    assert helper.resolve_data_dir(env=env) == tmp_path


def test_falls_back_to_home_when_env_unset(helper, capsys: pytest.CaptureFixture[str]) -> None:
    result = helper.resolve_data_dir(env={})
    expected = Path.home() / ".claude" / "plugins" / "data" / "causal-decision-debugger"
    assert result == expected
    # Stderr warning so users notice if fallback fires unexpectedly inside Claude Code.
    captured = capsys.readouterr()
    assert "CLAUDE_PLUGIN_DATA unset" in captured.err
    assert str(expected) in captured.err


def test_empty_env_var_falls_back(helper) -> None:
    # Empty string is treated the same as unset to avoid `Path("")` returning cwd.
    assert helper.resolve_data_dir(env={"CLAUDE_PLUGIN_DATA": ""}) == (
        Path.home() / ".claude" / "plugins" / "data" / "causal-decision-debugger"
    )


def test_uses_os_environ_by_default(
    helper, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert helper.resolve_data_dir() == tmp_path


def test_returns_pathlib_path(helper, tmp_path: Path) -> None:
    result = helper.resolve_data_dir(env={"CLAUDE_PLUGIN_DATA": str(tmp_path)})
    assert isinstance(result, Path)
