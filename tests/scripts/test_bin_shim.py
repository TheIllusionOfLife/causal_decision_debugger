"""Tests for the ``bin/causal-debugger`` plugin shim.

The shim is the executable Claude Code's Bash tool resolves when a session has
this plugin enabled. It must dispatch to the venv binary (created by
``bootstrap.py``) when present, and fail with a helpful message — not silently
— when the venv hasn't been bootstrapped yet.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM_PATH = REPO_ROOT / "bin" / "causal-debugger"
SCRIPTS_DIR = REPO_ROOT / "skills" / "diagnose" / "scripts"


def _load_shim():
    """Load the shim as a module so its functions are unit-testable.

    The shim has no ``.py`` extension (it's a CLI executable resolved by
    ``$PATH``), so ``spec_from_file_location`` needs an explicit
    ``SourceFileLoader``.
    """
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    loader = importlib.machinery.SourceFileLoader("causal_debugger_shim", str(SHIM_PATH))
    spec = importlib.util.spec_from_loader("causal_debugger_shim", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def shim():
    return _load_shim()


def test_shim_file_exists_and_is_executable() -> None:
    assert SHIM_PATH.exists(), f"missing {SHIM_PATH}"
    assert os.access(SHIM_PATH, os.X_OK), f"{SHIM_PATH} is not executable"


def test_shim_has_python_shebang() -> None:
    first_line = SHIM_PATH.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!"), f"missing shebang on {SHIM_PATH}"
    assert "python" in first_line, f"shebang does not invoke python: {first_line!r}"


def test_main_dispatches_to_venv_when_present(
    shim, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Lay down a fake venv binary at the location the shim expects.
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake_cli = venv_bin / "causal-debugger"
    fake_cli.write_text("#!/bin/sh\nexit 42\n")
    fake_cli.chmod(0o755)

    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

    captured: list[list[str]] = []

    def fake_call(cmd, **kwargs):
        del kwargs
        captured.append(list(cmd))
        return 7

    monkeypatch.setattr(shim.subprocess, "call", fake_call)

    rc = shim.main(["pipeline", "examples/onboarding_retention"])
    assert rc == 7
    assert len(captured) == 1
    assert captured[0][0] == str(fake_cli)
    assert captured[0][1:] == ["pipeline", "examples/onboarding_retention"]


def test_main_prints_helpful_error_when_venv_missing(
    shim, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

    rc = shim.main([])
    err = capsys.readouterr().err
    assert rc == 127
    assert "not installed" in err.lower()
    assert "bootstrap.py" in err


def test_error_message_uses_resolved_path_not_literal_env_var(
    shim, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Codex: the shim runs in many contexts (some without ``CLAUDE_PLUGIN_ROOT``
    set). Derive the bootstrap script path from ``__file__`` and print the
    resolved absolute path, not a literal ``${CLAUDE_PLUGIN_ROOT}/...``
    placeholder the user would have to interpret."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

    shim.main([])
    err = capsys.readouterr().err

    assert "${CLAUDE_PLUGIN_ROOT}" not in err
    assert "${" not in err
    # Should contain a real, resolvable absolute path.
    assert "bootstrap.py" in err
    bootstrap_abs = REPO_ROOT / "skills" / "diagnose" / "scripts" / "bootstrap.py"
    assert str(bootstrap_abs) in err


def test_shim_uses_subprocess_call_not_execv() -> None:
    """Codex: ``os.execv`` breaks stdout/stderr capture on Windows. The shim
    must use ``subprocess.call`` for cross-platform parent-process semantics."""
    source = SHIM_PATH.read_text(encoding="utf-8")
    assert "os.execv" not in source, "shim must not use os.execv (breaks Windows stdout capture)"
    assert "subprocess.call" in source, "shim must dispatch via subprocess.call"


def test_shim_runs_end_to_end_via_real_subprocess(tmp_path: Path) -> None:
    """Smoke test: actually invoke the shim as the OS would. Confirms the
    shebang resolves, sys.path manipulation works, and dispatch happens."""
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake_cli = venv_bin / "causal-debugger"
    # Echo args so we can assert the shim forwarded them correctly.
    fake_cli.write_text('#!/bin/sh\necho "forwarded:$*"\nexit 0\n')
    fake_cli.chmod(0o755)

    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    result = subprocess.run(
        [str(SHIM_PATH), "doctor", "--quiet"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        check=False,
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert "forwarded:doctor --quiet" in result.stdout
