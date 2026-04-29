"""Single source of truth for the plugin's data-directory path.

Both ``bootstrap.py`` and ``bin/causal-debugger`` import this helper so they
agree on where the venv lives. Without it, the two would drift the moment
either file is edited in isolation.

The plugin installs into ``${CLAUDE_PLUGIN_DATA}/venv/`` when run inside Claude
Code (the env var is always set there, resolving to a per-plugin path under
``~/.claude/plugins/data/{id}/``). Outside Claude Code (CI, ad-hoc terminal use)
the env var is unset, so we fall back to a canonical path keyed on the plugin
name. The fallback omits any marketplace-id suffix because there is no
marketplace context outside Claude Code; a stderr warning makes the fallback
visible if it ever fires when it shouldn't.

Stdlib only: this file is imported by ``bin/causal-debugger`` before the venv
exists, so it cannot depend on installed packages.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

_FALLBACK_PLUGIN_DIR = ".claude/plugins/data/causal-decision-debugger"


def resolve_data_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the plugin's data directory.

    Reads ``CLAUDE_PLUGIN_DATA`` from ``env`` (defaults to ``os.environ``). When
    the variable is set and non-empty, returns it verbatim. Otherwise prints a
    one-line warning to stderr and returns the canonical fallback under the
    user's home directory.
    """
    source = os.environ if env is None else env
    raw = source.get("CLAUDE_PLUGIN_DATA", "")
    if raw:
        return Path(raw)
    fallback = Path.home() / _FALLBACK_PLUGIN_DIR
    print(
        f"CLAUDE_PLUGIN_DATA unset; using fallback data dir at {fallback} "
        f"(this is normal for CI/dev outside Claude Code)",
        file=sys.stderr,
    )
    return fallback
