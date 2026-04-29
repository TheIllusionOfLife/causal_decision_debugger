#!/usr/bin/env python3
"""Install the bundled ``causal-debugger`` wheel on first use.

Stdlib-only by design: this script must run on a fresh machine with nothing
beyond Python 3.11+. It tries ``uv tool install`` → ``pipx install`` →
``python -m pip install --user`` in order, and verifies that the
``causal-debugger`` console script is reachable on ``$PATH`` afterwards.

Idempotent: skips installation when ``causal-debugger doctor`` already
reports the bundled version *and* schemas are resolvable. ``doctor`` exits
non-zero when schemas cannot be loaded, so a corrupted install at the same
version is detected here instead of being silently accepted.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import site
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


def _existing_install() -> tuple[str | None, str | None, str | None]:
    """Return (cli_path, version, metadata_sha256) for a healthy install.

    Health is decided by ``causal-debugger doctor``: if the schemas can't be
    loaded (a corrupted install), doctor exits non-zero and we treat the
    install as broken so the bootstrap re-installs instead of accepting it.
    The returned ``metadata_sha256`` lets the caller distinguish "same
    version, same source" from "same version, rebuilt source" — the version
    string alone can't.
    """
    cli = shutil.which("causal-debugger")
    if cli is None:
        return None, None, None
    try:
        out = subprocess.run(
            [cli, "doctor"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return cli, None, None
    if out.returncode != 0:
        return cli, None, None
    try:
        info = json.loads(out.stdout)
    except json.JSONDecodeError:
        return cli, None, None
    version = info.get("package_version")
    metadata_sha = info.get("metadata_sha256")
    return (
        cli,
        version if isinstance(version, str) else None,
        metadata_sha if isinstance(metadata_sha, str) else None,
    )


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
    """Install commands tried in order.

    ``--python sys.executable`` (rather than a hard-coded "3.11") so users on
    Python 3.12+ also work — the script's own version guard already enforces
    the 3.11 floor. ``--force`` / ``--upgrade`` ensure the existing install is
    replaced when the bundled wheel version moves forward instead of silently
    falling through to the next installer and leaving two copies on disk.
    """
    py = sys.executable
    attempts: list[list[str]] = []
    if shutil.which("uv"):
        attempts.append(["uv", "tool", "install", "--force", "--python", py, str(wheel)])
    if shutil.which("pipx"):
        attempts.append(["pipx", "install", "--force", "--python", py, str(wheel)])
    attempts.append([py, "-m", "pip", "install", "--user", "--upgrade", str(wheel)])
    return attempts


def _candidate_bin_dirs() -> list[Path]:
    """Every directory the three install paths might drop the script into.

    - ``pip install --user`` puts it at ``site.getuserbase()/bin``: stock
      macOS Python lands in ``~/Library/Python/X.Y/bin``, Linux in
      ``~/.local/bin``.
    - ``uv tool install`` and ``pipx install`` both default to
      ``~/.local/bin`` on every platform (overridable via
      ``UV_TOOL_BIN_DIR`` / ``PIPX_BIN_DIR``, but defaults cover the
      common case).

    On Linux these collapse to one path; on macOS they're two distinct
    directories. The post-install error iterates both so the user sees the
    one that actually applies to whichever installer succeeded.
    """
    pip_user_bin = Path(site.getuserbase()) / "bin"
    uv_pipx_bin = Path.home() / ".local" / "bin"
    return [pip_user_bin] if pip_user_bin == uv_pipx_bin else [pip_user_bin, uv_pipx_bin]


def _post_install_check(expected_version: str) -> int:
    cli = shutil.which("causal-debugger")
    if cli is None:
        bin_dirs = _candidate_bin_dirs()
        suggestions = "\n".join(f'  export PATH="{p}:$PATH"' for p in bin_dirs)
        return _die(
            "install reported success but `causal-debugger` is not on $PATH.\n"
            "It probably landed in one of these (uv/pipx default to ~/.local/bin; "
            "pip --user uses site.getuserbase()/bin). Add the relevant one to your "
            "shell profile:\n"
            f"{suggestions}\n"
            "Then re-run this bootstrap."
        )
    cli, version, _ = _existing_install()
    if version is None:
        return _die(
            f"installed at {cli} but `causal-debugger doctor` failed.\n"
            "Run it directly to see the error; a re-bootstrap may be needed."
        )
    if version != expected_version:
        return _die(
            f"installed version {version} does not match bundled {expected_version}.\n"
            f"Likely an older `causal-debugger` is shadowing on $PATH at {cli}.\n"
            "Uninstall the previous copy (`uv tool uninstall causal-debugger` or "
            "`pipx uninstall causal-debugger`) and re-run this bootstrap."
        )
    print(f"READY: causal-debugger {version} at {cli}")
    return 0


def main() -> int:
    err = _check_python()
    if err is not None:
        return err

    # Catch the full set of "manifest is unusable" failure modes (missing,
    # malformed JSON, missing required keys, wrong type) so the user gets a
    # readable bootstrap error and not a Python traceback.
    try:
        manifest = _read_manifest()
        wheel = _wheel_path(manifest)
        required_keys = ("wheel", "sha256", "metadata_sha256", "version")
        missing = [k for k in required_keys if k not in manifest]
        if missing:
            raise KeyError(f"manifest is missing required keys: {missing}")
    except FileNotFoundError as exc:
        return _die(str(exc))
    except json.JSONDecodeError as exc:
        return _die(f"manifest.json is not valid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _die(f"manifest.json is malformed: {exc!r}")

    err = _verify_manifest(manifest, wheel)
    if err is not None:
        return err

    cli, version, metadata_sha = _existing_install()
    # Compare the metadata fingerprint as well as the version: a same-version
    # rebuild (source changed without bumping ``project.version``) leaves the
    # version string equal but the METADATA hash different, and we want to
    # reinstall in that case. ``metadata_sha`` is None on older installs that
    # don't expose the field — treat that as "needs reinstall" too.
    if (
        cli is not None
        and version == manifest["version"]
        and metadata_sha == manifest["metadata_sha256"]
    ):
        print(f"READY: causal-debugger {version} already installed at {cli}")
        return 0

    failures: list[tuple[str, str]] = []
    for cmd in _install_attempts(wheel):
        print(f"bootstrap: trying {' '.join(cmd[:3])}...", file=sys.stderr)
        ok, out = _try_install(cmd)
        if ok:
            return _post_install_check(manifest["version"])
        failures.append((" ".join(cmd), out))

    # Keep the last ~20 lines of each installer's output. Pip/uv dependency
    # resolution errors are usually multi-line (resolver trace + the actual
    # conflict), and a single-line tail loses the context a user needs.
    print("bootstrap: every install method failed:", file=sys.stderr)
    for cmd_str, output in failures:
        print(f"  - {cmd_str}", file=sys.stderr)
        lines = output.strip().splitlines() if output.strip() else ["<no output>"]
        for line in lines[-20:]:
            print(f"      {line}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
