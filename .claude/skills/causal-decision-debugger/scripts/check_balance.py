#!/usr/bin/env python
"""Thin shim: ``causal_debugger.data.balance``."""

from __future__ import annotations

import sys

from causal_debugger.data.balance import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
