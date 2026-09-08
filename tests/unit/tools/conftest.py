"""Make tools/manufacturing importable for the tools tests."""

import os
import sys

TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "tools", "manufacturing")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
