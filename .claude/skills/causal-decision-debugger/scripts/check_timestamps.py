#!/usr/bin/env python
"""Thin shim: ``causal_debugger.data.timestamps``."""

from __future__ import annotations

import sys

from causal_debugger.data.timestamps import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
