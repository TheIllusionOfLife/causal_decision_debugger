#!/usr/bin/env python3
"""Install the bundled ``causal-debugger`` wheel into the plugin's data dir.

Stdlib-only by design: this script must run on a fresh machine with nothing
beyond Python 3.11+. It creates a virtualenv at ``${CLAUDE_PLUGIN_DATA}/venv/``
(via :mod:`venv`) and installs the bundled wheel into it with pip. The venv
lives in the per-plugin persistent data directory documented in the Claude
Code plugin reference, so heavy transitive dependencies (``pandas``, ``scipy``,
``scikit-learn``, ``dowhy``, ``econml``) survive plugin updates and only
re-resolve when the bundled wheel's metadata fingerprint changes.

Idempotent: skips installation when ``install_manifest.json`` records the same
``metadata_sha256`` as the bundled wheel and both ``venv/bin/python`` and
``venv/bin/causal-debugger`` exist on disk.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _install_paths import resolve_data_dir

VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"
MANIFEST_PATH = VENDOR_DIR / "manifest.json"
MIN_PYTHON = (3, 11)
INSTALL_TIME_WARNING = (
    "First-run install will download ~500 MB and take 5-30 minutes "
    "(pandas, scipy, scikit-learn, dowhy, econml). Subsequent runs are instant."
)


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


def read_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"missing {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _wheel_path(manifest: dict) -> Path:
    wheel = (VENDOR_DIR / manifest["wheel"]).resolve()
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


def venv_paths(data_dir: Path) -> tuple[Path, Path]:
    """Return ``(python, causal-debugger)`` paths inside ``<data_dir>/venv``.

    Windows uses ``Scripts/`` and ``.exe`` suffix; Unix uses ``bin/`` and bare
    names. The pip install layout is determined by the host ``venv`` module.
    """
    venv = data_dir / "venv"
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe", venv / "Scripts" / "causal-debugger.exe"
    return venv / "bin" / "python", venv / "bin" / "causal-debugger"


def is_install_current(data_dir: Path, manifest: dict) -> bool:
    """True iff the installed venv matches the bundled wheel's full fingerprint.

    Compares both ``metadata_sha256`` (catches dependency-graph changes) and
    ``sha256`` (catches code-only changes that leave METADATA untouched). Both
    ``venv/bin/python`` and ``venv/bin/causal-debugger`` must exist — Codex
    flagged that the doctor smoke test catches runtime errors but not a missing
    console-script entry point.
    """
    install_manifest = data_dir / "install_manifest.json"
    if not install_manifest.exists():
        return False
    try:
        recorded = json.loads(install_manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if recorded.get("metadata_sha256") != manifest.get("metadata_sha256"):
        return False
    if recorded.get("sha256") != manifest.get("sha256"):
        return False
    python, cli = venv_paths(data_dir)
    return python.exists() and cli.exists()


def has_partial_venv(data_dir: Path) -> bool:
    """A venv directory that has no install_manifest.json beside it.

    Indicates a previous bootstrap was interrupted mid-install; the next
    bootstrap must wipe the venv (``python -m venv --clear``) before
    reinstalling, otherwise stale half-installed packages cause insidious
    runtime failures.
    """
    return (data_dir / "venv").exists() and not (data_dir / "install_manifest.json").exists()


def write_install_manifest(data_dir: Path, manifest: dict) -> None:
    """Write ``install_manifest.json`` atomically via temp file + ``os.replace``.

    A crash mid-write must not leave a partial file that would fool the next
    idempotency check into skipping a reinstall.
    """
    payload = {
        "metadata_sha256": manifest["metadata_sha256"],
        "version": manifest["version"],
        "wheel": manifest["wheel"],
        "sha256": manifest["sha256"],
    }
    target = data_dir / "install_manifest.json"
    tmp = data_dir / "install_manifest.json.tmp"
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, target)


@contextlib.contextmanager
def bootstrap_lock(data_dir: Path, *, blocking: bool = True) -> Iterator[None]:
    """Exclusive file lock at ``<data_dir>/.bootstrap.lock``.

    Two simultaneous Claude Code sessions running bootstrap can corrupt the
    venv. ``fcntl.flock`` (Unix) and ``msvcrt.locking`` (Windows) provide
    process-level exclusion. With ``blocking=False`` the lock raises
    ``BlockingIOError`` if held; the default waits.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / ".bootstrap.lock"
    fh = lock_path.open("w")
    try:
        if sys.platform == "win32":
            mode = msvcrt.LK_NBLCK if not blocking else msvcrt.LK_LOCK
            try:
                msvcrt.locking(fh.fileno(), mode, 1)
            except OSError as exc:
                raise BlockingIOError("bootstrap lock held") from exc
        else:
            flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if not blocking else 0)
            fcntl.flock(fh.fileno(), flags)
        yield
    finally:
        try:
            if sys.platform == "win32":
                with contextlib.suppress(OSError):
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def _create_venv(data_dir: Path, *, clear: bool) -> int:
    venv_dir = data_dir / "venv"
    cmd = [sys.executable, "-m", "venv"]
    if clear:
        cmd.append("--clear")
    cmd.append(str(venv_dir))
    print(f"bootstrap: {'recreating' if clear else 'creating'} venv at {venv_dir}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        return _die(
            f"`python -m venv {venv_dir}` failed (exit {result.returncode}):\n"
            f"{(result.stderr or result.stdout or '<no output>').strip()}"
        )
    return 0


def _install_wheel(data_dir: Path, wheel: Path) -> int:
    python, _ = venv_paths(data_dir)
    cmd = [str(python), "-m", "pip", "install", str(wheel)]
    print(f"bootstrap: installing {wheel.name} (this is the slow step)", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=False)
    if result.returncode != 0:
        tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-30:])
        return _die(f"pip install failed (exit {result.returncode}):\n{tail}")
    return 0


def _smoke_test(data_dir: Path, manifest: dict) -> int:
    _, cli = venv_paths(data_dir)
    if not cli.exists():
        return _die(f"installed venv is missing {cli}")
    result = subprocess.run(
        [str(cli), "doctor"], capture_output=True, text=True, timeout=30, check=False
    )
    if result.returncode != 0:
        return _die(
            f"`causal-debugger doctor` failed (exit {result.returncode}):\n"
            f"{(result.stderr or result.stdout or '<no output>').strip()}"
        )
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return _die(f"doctor returned non-JSON output: {exc}\n{result.stdout}")
    if not info.get("schemas_resolvable"):
        return _die(f"doctor reports schemas_resolvable=false: {info.get('schemas_error')}")
    if info.get("metadata_sha256") != manifest["metadata_sha256"]:
        return _die(
            f"doctor reports metadata_sha256={info.get('metadata_sha256')} "
            f"but bundled wheel is {manifest['metadata_sha256']}"
        )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override the plugin data dir (defaults to $CLAUDE_PLUGIN_DATA or fallback).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    err = _check_python()
    if err is not None:
        return err

    try:
        manifest = read_manifest()
        wheel = _wheel_path(manifest)
        required = ("wheel", "sha256", "metadata_sha256", "version")
        missing = [k for k in required if k not in manifest]
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

    data_dir = args.data_dir if args.data_dir is not None else resolve_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    with bootstrap_lock(data_dir):
        if is_install_current(data_dir, manifest):
            _, cli = venv_paths(data_dir)
            print(f"READY: causal-debugger {manifest['version']} already installed at {cli}")
            return 0

        venv_dir = data_dir / "venv"
        partial = has_partial_venv(data_dir)
        stale = venv_dir.exists() and not partial
        clear = partial or stale
        if partial:
            print(
                "bootstrap: detected partial venv (no install_manifest.json) — wiping",
                file=sys.stderr,
            )
        elif stale:
            print(
                "bootstrap: existing venv does not match bundled wheel fingerprint — wiping",
                file=sys.stderr,
            )

        print(f"bootstrap: {INSTALL_TIME_WARNING}", file=sys.stderr)
        if (rc := _create_venv(data_dir, clear=clear)) != 0:
            return rc
        if (rc := _install_wheel(data_dir, wheel)) != 0:
            return rc
        if (rc := _smoke_test(data_dir, manifest)) != 0:
            return rc

        write_install_manifest(data_dir, manifest)
        _, cli = venv_paths(data_dir)
        print(f"READY: causal-debugger {manifest['version']} at {cli}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
