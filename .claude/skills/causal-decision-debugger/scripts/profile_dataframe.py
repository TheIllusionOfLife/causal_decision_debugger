#!/usr/bin/env python
"""Thin shim: ``causal_debugger.data.profile``."""

from __future__ import annotations

import sys

from causal_debugger.data.profile import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
