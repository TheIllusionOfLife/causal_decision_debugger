#!/usr/bin/env python
"""Thin shim: ``causal_debugger.methods.router``."""

from __future__ import annotations

import sys

from causal_debugger.methods.router import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
