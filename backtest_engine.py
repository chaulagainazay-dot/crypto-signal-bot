#!/usr/bin/env python3
"""
backtest_engine.py  (root entry point)
Thin wrapper that delegates to the backtest_engine package.
Kept for backward compatibility with existing CLI calls.
"""

import sys
from backtest_engine.main import main

if __name__ == "__main__":
    sys.exit(main() or 0)
