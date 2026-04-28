#!/usr/bin/env python3
"""Install the bundled ``causal-debugger`` wheel on first use.

Stdlib-only by design: this script must run on a fresh machine with nothing
beyond Python 3.11+. It tries ``uv tool install`` → ``pipx install`` →
``python -m pip install --user`` in order, and verifies that the
``causal-debugger`` console script is reachable on ``$PATH`` afterwards.

Idempotent: if the bundled wheel's SHA256 matches what is already installed,
exits 0 without re-installing.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"
MANIFEST_PATH = VENDOR_DIR / "manifest.json"
MIN_PYTHON = (3, 11)


def _die(msg: str, code: int = 1) -> int:
    print(f"bootstrap: {msg}", file=sys.stderr)
    return code


def _check_python() -> int | None:
    if sys.version_info < MIN_PYTHON:
        return _die(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, found "
            f"{sys.version_info.major}.{sys.version_info.minor}."
        )
    return None


def _read_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"missing {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _wheel_path(manifest: dict) -> Path:
    wheel = VENDOR_DIR / manifest["wheel"]
    if not wheel.exists():
        raise FileNotFoundError(f"missing wheel {wheel}")
    return wheel


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_manifest(manifest: dict, wheel: Path) -> int | None:
    actual = _sha256(wheel)
    if actual != manifest["sha256"]:
        return _die(
            f"vendored wheel sha256 mismatch.\n  manifest: {manifest['sha256']}\n  actual:   {actual}\n"
            "Re-build the wheel and refresh manifest.json."
        )
    return None


def _existing_install() -> tuple[str | None, str | None]:
    """Return (cli_path, version) if causal-debugger is already callable."""
    cli = shutil.which("causal-debugger")
    if cli is None:
        return None, None
    try:
        out = subprocess.run(
            [cli, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return cli, None
    if out.returncode != 0:
        return cli, None
    parts = out.stdout.strip().split()
    return cli, parts[-1] if parts else None


def _try_install(cmd: list[str]) -> tuple[bool, str]:
    """Run an install command; return (success, combined_output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    except FileNotFoundError:
        return False, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return False, f"{cmd[0]} timed out after 600s"
    out = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, out


def _install_attempts(wheel: Path) -> list[list[str]]:
    attempts: list[list[str]] = []
    if shutil.which("uv"):
        attempts.append(["uv", "tool", "install", "--python", "3.11", str(wheel)])
    if shutil.which("pipx"):
        attempts.append(["pipx", "install", "--python", "python3.11", str(wheel)])
    attempts.append([sys.executable, "-m", "pip", "install", "--user", str(wheel)])
    return attempts


def _user_base_bin() -> Path:
    if sys.platform == "darwin":
        # pip --user lands here on stock macOS Python.
        return (
            Path.home()
            / "Library"
            / "Python"
            / f"{sys.version_info.major}.{sys.version_info.minor}"
            / "bin"
        )
    return Path.home() / ".local" / "bin"


def _post_install_check(expected_version: str) -> int:
    cli, version = _existing_install()
    if cli is None:
        bin_dir = _user_base_bin()
        return _die(
            "install reported success but `causal-debugger` is not on $PATH.\n"
            f"It probably landed in {bin_dir}. Add this to your shell profile:\n"
            f'  export PATH="{bin_dir}:$PATH"\n'
            "Then re-run this bootstrap."
        )
    if version != expected_version:
        print(
            f"bootstrap: warning — installed version {version} differs from bundled {expected_version}",
            file=sys.stderr,
        )
    print(f"READY: causal-debugger {version} at {cli}")
    return 0


def main() -> int:
    err = _check_python()
    if err is not None:
        return err

    try:
        manifest = _read_manifest()
        wheel = _wheel_path(manifest)
    except FileNotFoundError as exc:
        return _die(str(exc))

    err = _verify_manifest(manifest, wheel)
    if err is not None:
        return err

    cli, version = _existing_install()
    if cli is not None and version == manifest["version"]:
        print(f"READY: causal-debugger {version} already installed at {cli}")
        return 0

    failures: list[tuple[str, str]] = []
    for cmd in _install_attempts(wheel):
        print(f"bootstrap: trying {' '.join(cmd[:3])}...", file=sys.stderr)
        ok, out = _try_install(cmd)
        if ok:
            return _post_install_check(manifest["version"])
        failures.append(
            (" ".join(cmd), out.strip().splitlines()[-1] if out.strip() else "<no output>")
        )

    print("bootstrap: every install method failed:", file=sys.stderr)
    for cmd_str, last in failures:
        print(f"  - {cmd_str}\n      {last}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
