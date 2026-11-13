#!/usr/bin/env python3
"""Run the BDB-5 synthetic offline harness from the repository root."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
