"""Tests for the venv-based bootstrap script.

The slow parts (real ``python -m venv``, real ``pip install`` of pandas /
scipy / dowhy) are exercised by the install-test CI workflow, not here. These
tests cover the logic that decides *whether* to run those slow operations:
idempotency, partial-install detection, atomic manifest writes, file locking,
and the "validate both binaries" guard Codex flagged.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skills" / "diagnose" / "scripts"
BOOTSTRAP_PATH = SCRIPTS_DIR / "bootstrap.py"

_SAMPLE_MANIFEST = {
    "wheel": "causal_debugger-0.2.0-py3-none-any.whl",
    "sha256": "deadbeef" * 8,
    "metadata_sha256": "feedface" * 8,
    "version": "0.2.0",
    "entry_points": ["causal-debugger"],
}


def _load_bootstrap():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("bootstrap", BOOTSTRAP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bootstrap():
    return _load_bootstrap()


def _make_fake_venv(data_dir: Path, *, with_cli: bool = True) -> None:
    """Create a venv-shaped directory with python (always) and optionally the CLI."""
    bin_dir = data_dir / "venv" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "python").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "python").chmod(0o755)
    if with_cli:
        (bin_dir / "causal-debugger").write_text("#!/bin/sh\nexit 0\n")
        (bin_dir / "causal-debugger").chmod(0o755)


def _write_install_manifest(data_dir: Path, manifest: dict[str, Any]) -> None:
    (data_dir / "install_manifest.json").write_text(json.dumps(manifest))


# ---------------------------------------------------------------------------
# venv path helpers
# ---------------------------------------------------------------------------


def test_venv_paths(bootstrap, tmp_path: Path) -> None:
    python, cli = bootstrap.venv_paths(tmp_path)
    assert python == tmp_path / "venv" / "bin" / "python"
    assert cli == tmp_path / "venv" / "bin" / "causal-debugger"


# ---------------------------------------------------------------------------
# is_install_current — the idempotency check
# ---------------------------------------------------------------------------


def test_is_install_current_true_when_everything_matches(bootstrap, tmp_path: Path) -> None:
    _make_fake_venv(tmp_path, with_cli=True)
    _write_install_manifest(
        tmp_path,
        {"metadata_sha256": _SAMPLE_MANIFEST["metadata_sha256"], "version": "0.2.0"},
    )
    assert bootstrap.is_install_current(tmp_path, _SAMPLE_MANIFEST) is True


def test_is_install_current_false_when_manifest_missing(bootstrap, tmp_path: Path) -> None:
    _make_fake_venv(tmp_path, with_cli=True)
    assert bootstrap.is_install_current(tmp_path, _SAMPLE_MANIFEST) is False


def test_is_install_current_false_when_metadata_hash_mismatch(bootstrap, tmp_path: Path) -> None:
    _make_fake_venv(tmp_path, with_cli=True)
    _write_install_manifest(tmp_path, {"metadata_sha256": "different", "version": "0.2.0"})
    assert bootstrap.is_install_current(tmp_path, _SAMPLE_MANIFEST) is False


def test_is_install_current_false_when_cli_binary_missing(bootstrap, tmp_path: Path) -> None:
    """Codex: validate both python AND causal-debugger — doctor catches runtime
    errors but not a missing console-script entry point."""
    _make_fake_venv(tmp_path, with_cli=False)
    _write_install_manifest(
        tmp_path,
        {"metadata_sha256": _SAMPLE_MANIFEST["metadata_sha256"], "version": "0.2.0"},
    )
    assert bootstrap.is_install_current(tmp_path, _SAMPLE_MANIFEST) is False


def test_is_install_current_false_when_install_manifest_corrupt(bootstrap, tmp_path: Path) -> None:
    _make_fake_venv(tmp_path, with_cli=True)
    (tmp_path / "install_manifest.json").write_text("not json{{{")
    assert bootstrap.is_install_current(tmp_path, _SAMPLE_MANIFEST) is False


# ---------------------------------------------------------------------------
# partial-venv detection
# ---------------------------------------------------------------------------


def test_has_partial_venv_true_when_venv_exists_without_manifest(bootstrap, tmp_path: Path) -> None:
    _make_fake_venv(tmp_path, with_cli=True)
    assert bootstrap.has_partial_venv(tmp_path) is True


def test_has_partial_venv_false_when_no_venv(bootstrap, tmp_path: Path) -> None:
    assert bootstrap.has_partial_venv(tmp_path) is False


def test_has_partial_venv_false_when_manifest_present(bootstrap, tmp_path: Path) -> None:
    _make_fake_venv(tmp_path, with_cli=True)
    _write_install_manifest(tmp_path, {"metadata_sha256": "x", "version": "0.2.0"})
    assert bootstrap.has_partial_venv(tmp_path) is False


# ---------------------------------------------------------------------------
# atomic manifest write
# ---------------------------------------------------------------------------


def test_write_install_manifest_uses_temp_then_rename(
    bootstrap, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex: write to .tmp then os.replace, so a crash mid-write never leaves
    a partial install_manifest.json that fools the next idempotency check."""
    rename_calls: list[tuple[str, str]] = []

    real_replace = bootstrap.os.replace

    def spy_replace(src: str, dst: str) -> None:
        rename_calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(bootstrap.os, "replace", spy_replace)
    bootstrap.write_install_manifest(tmp_path, _SAMPLE_MANIFEST)

    assert len(rename_calls) == 1
    src, dst = rename_calls[0]
    assert src.endswith(".tmp")
    assert dst.endswith("install_manifest.json")

    saved = json.loads((tmp_path / "install_manifest.json").read_text())
    assert saved["metadata_sha256"] == _SAMPLE_MANIFEST["metadata_sha256"]
    assert saved["version"] == "0.2.0"


# ---------------------------------------------------------------------------
# file lock — concurrent invocations
# ---------------------------------------------------------------------------


def test_lock_is_exclusive_within_same_process(bootstrap, tmp_path: Path) -> None:
    """Two concurrent invocations would corrupt the venv. The first acquires
    an exclusive lock; a second non-blocking attempt fails."""
    with (
        bootstrap.bootstrap_lock(tmp_path),
        pytest.raises(BlockingIOError),
        bootstrap.bootstrap_lock(tmp_path, blocking=False),
    ):
        pass


# ---------------------------------------------------------------------------
# main() flow with mocked subprocess (no real pip install)
# ---------------------------------------------------------------------------


def test_main_skips_install_when_already_current(
    bootstrap, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fake_venv(data_dir, with_cli=True)
    _write_install_manifest(
        data_dir,
        {"metadata_sha256": bootstrap.read_manifest()["metadata_sha256"], "version": "0.2.0"},
    )

    pip_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        del kwargs
        pip_calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)
    rc = bootstrap.main(["--data-dir", str(data_dir)])

    assert rc == 0
    assert pip_calls == [], "should not invoke pip when install is current"


def test_main_force_rebuilds_on_partial_venv(
    bootstrap, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex: if venv exists but install_manifest.json doesn't, --clear the venv
    before reinstalling. Half-installed packages cause insidious failures."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _make_fake_venv(data_dir, with_cli=True)  # venv present
    # No install_manifest.json — looks like a partial install.

    invocations: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        del kwargs
        invocations.append(list(cmd))
        # Simulate the venv getting (re)created so subsequent steps find python.
        if "venv" in cmd:
            _make_fake_venv(data_dir, with_cli=True)
        # Doctor smoke test: pretend it succeeded with the right metadata.
        if cmd[-1] == "doctor":
            stdout = json.dumps(
                {
                    "schemas_resolvable": True,
                    "package_version": "0.2.0",
                    "metadata_sha256": bootstrap.read_manifest()["metadata_sha256"],
                }
            )
            return subprocess.CompletedProcess(cmd, 0, stdout, "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    rc = bootstrap.main(["--data-dir", str(data_dir)])
    assert rc == 0
    venv_create_cmds = [c for c in invocations if "venv" in c]
    assert any("--clear" in c for c in venv_create_cmds), (
        f"expected --clear on partial-venv rebuild, got: {venv_create_cmds}"
    )


def test_main_writes_install_manifest_only_after_successful_smoke_test(
    bootstrap, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If `causal-debugger doctor` reports schemas_resolvable=False, do NOT
    write install_manifest.json — otherwise the broken install would be
    treated as current next time."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    def fake_run(cmd, **kwargs):
        del kwargs
        if "venv" in cmd:
            _make_fake_venv(data_dir, with_cli=True)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[-1] == "doctor":
            stdout = json.dumps({"schemas_resolvable": False, "schemas_error": "boom"})
            return subprocess.CompletedProcess(cmd, 1, stdout, "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    rc = bootstrap.main(["--data-dir", str(data_dir)])
    assert rc != 0
    assert not (data_dir / "install_manifest.json").exists()
