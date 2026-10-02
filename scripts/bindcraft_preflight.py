#!/usr/bin/env python3
"""Compatibility shim — canonical gate lives in stage2_preflight.py.

Kept so older notebook cells / upload instructions that reference
bindcraft_preflight.py keep working after the reliability-consolidation
refactor. No gate logic is duplicated here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stage2_preflight import *  # noqa: E402,F401,F403
from stage2_preflight import main  # noqa: E402,F401

if __name__ == "__main__":
    sys.exit(main())
