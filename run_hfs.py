#!/usr/bin/env python
"""Launch HFS TUI."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hfs.tui import HFSApp

if __name__ == "__main__":
    HFSApp().run()
