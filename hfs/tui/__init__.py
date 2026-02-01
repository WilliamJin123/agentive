"""HFS Terminal User Interface package.

This package provides the Textual-based TUI for the Hexagonal Frontend System.
The main entry point is HFSApp, which provides an interactive REPL for
chatting with the HFS agents.
"""

from .app import HFSApp

__all__ = ["HFSApp"]
