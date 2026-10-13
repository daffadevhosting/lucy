#!/usr/bin/env python3
"""Convenience launcher for Lucy."""

import sys
from pathlib import Path

# Ensure src/ is on PYTHONPATH
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from lucy.main import main

if __name__ == "__main__":
    main()
