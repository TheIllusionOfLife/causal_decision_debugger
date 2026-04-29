"""``causal-debugger`` console entry point.

Pure dispatch to the existing ``main(argv)`` functions in each module so that
external callers (Skill, agents, CI smoke tests) have a single stable command
surface and never need to remember per-module ``python -m`` paths.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_SUBCOMMANDS: dict[str, tuple[str, str]] = {
    "validate-spec": (
        "causal_debugger.spec.validate",
        "Validate a causal_spec.yaml against the JSON schema.",
    ),
    "profile": (
        "causal_debugger.data.profile",
        "Profile a dataframe (missingness, cardinality, ranges).",
    ),
    "check-timestamps": (
        "causal_debugger.data.timestamps",
        "Check that treatment time precedes outcome time.",
    ),
    "check-balance": (
        "causal_debugger.data.balance",
        "Compute covariate balance / SMD between treatment groups.",
    ),
    "suggest-method": (
        "causal_debugger.methods.router",
        "Route a causal spec to an identification strategy.",
    ),
    "report": ("causal_debugger.reporting.render", "Render report.md from analysis artifacts."),
    "pipeline": (
        "causal_debugger.pipeline",
        "Run the full validate → audit → estimate → refute → render pipeline.",
    ),
}


def _load_main(module_path: str) -> Callable[[list[str] | None], int]:
    from importlib import import_module

    module = import_module(module_path)
    return module.main  # type: ignore[no-any-return]


def _package_version() -> str:
    try:
        return importlib.metadata.version("causal-debugger")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _installed_metadata_sha256() -> str | None:
    """SHA256 of the installed package's normalized METADATA.

    Bootstrap compares this against the bundled ``manifest.json`` so it can
    tell "same version, different source" apart from "same version, same
    source" — which the version string alone can't do when a wheel is
    rebuilt without bumping ``project.version``. Normalization (strip
    trailing whitespace per line, canonical trailing newline) matches the
    install-test workflow's hashing so both sides agree.
    """
    try:
        text = importlib.metadata.distribution("causal-debugger").read_text("METADATA")
    except importlib.metadata.PackageNotFoundError:
        return None
    if text is None:
        return None
    norm = "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _doctor(_: list[str]) -> int:
    cli_path = shutil.which("causal-debugger") or "<not on PATH>"
    # ``sys.executable`` is the venv's python under the canonical install
    # model (``${CLAUDE_PLUGIN_DATA}/venv/bin/python``). Reporting the venv
    # root lets bug reports show whether ``causal-debugger`` is dispatching
    # from the plugin venv or some other Python. Don't ``resolve()`` first —
    # that follows the symlink to the underlying Python install (e.g.
    # ``/opt/homebrew/.../python@3.11/...``) instead of the venv directory.
    venv_root = str(Path(sys.executable).parent.parent)
    info: dict[str, Any] = {
        "package_version": _package_version(),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "venv_root": venv_root,
        "causal_debugger_cli_on_path": cli_path,
        "platform": sys.platform,
        "metadata_sha256": _installed_metadata_sha256(),
    }
    try:
        from causal_debugger.schemas import load_schema

        load_schema("causal_spec")
        info["schemas_resolvable"] = True
    except Exception as exc:
        info["schemas_resolvable"] = False
        info["schemas_error"] = repr(exc)
    # ``allow_nan=False`` matches the pipeline's strict-JSON convention so a
    # surprise NaN/Inf in any future doctor field fails loudly. Exit non-zero
    # when schemas can't load — bootstrap relies on this to detect a corrupted
    # install at the same version string.
    print(json.dumps(info, indent=2, sort_keys=True, allow_nan=False))
    return 0 if info["schemas_resolvable"] else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="causal-debugger",
        description="Causal Decision Debugger CLI.",
    )
    parser.add_argument(
        "--version", action="version", version=f"causal-debugger {_package_version()}"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    for name, (_, help_text) in _SUBCOMMANDS.items():
        sub.add_parser(name, help=help_text, add_help=False)
    sub.add_parser("doctor", help="Print environment diagnostics for bug reports.", add_help=False)

    if not argv:
        parser.print_help(sys.stderr)
        return 2
    command, *rest = argv
    if command in {"-h", "--help"}:
        parser.print_help()
        return 0
    if command == "--version":
        print(f"causal-debugger {_package_version()}")
        return 0
    if command == "doctor":
        return _doctor(rest)
    if command not in _SUBCOMMANDS:
        parser.error(f"unknown command: {command!r}. Try `causal-debugger --help`.")
    module_path, _ = _SUBCOMMANDS[command]
    return _load_main(module_path)(rest)


if __name__ == "__main__":
    sys.exit(main())
