"""HFS Visual Theme.

This module defines the HFS visual theme for the Textual TUI. The theme
follows a yellow/amber color palette inspired by bees and hexagons,
with distinct colors for different triad types.

Colors:
    - Primary: #F59E0B (amber) - Main accent color
    - Hierarchical: #3B82F6 (blue) - For hierarchical triad elements
    - Dialectic: #A855F7 (purple) - For dialectic triad elements
    - Consensus: #22C55E (green) - For consensus triad elements

Usage:
    from hfs.tui.theme import HFS_THEME

    app.register_theme(HFS_THEME)
    app.theme = "hfs"
"""

from textual.theme import Theme

# HFS Theme Definition
# Yellow/amber palette with dark mode and triad-specific color variables
HFS_THEME = Theme(
    name="hfs",
    primary="#F59E0B",      # Amber/yellow - main accent
    secondary="#D97706",     # Darker amber
    accent="#FCD34D",        # Light yellow
    foreground="#F5F5F5",    # Light text
    background="#1A1A1A",    # Dark background
    surface="#262626",       # Slightly lighter surface
    panel="#333333",         # Panels and cards
    warning="#EAB308",       # Yellow warning
    error="#EF4444",         # Red error
    success="#22C55E",       # Green success
    dark=True,
    variables={
        # Triad type colors for visual distinction
        "hfs-hierarchical": "#3B82F6",   # Blue - structured/top-down
        "hfs-dialectic": "#A855F7",      # Purple - debate/synthesis
        "hfs-consensus": "#22C55E",       # Green - agreement/voting
        # Additional semantic variables
        "hfs-muted": "#737373",           # Muted text
        "hfs-border": "#404040",          # Border color
        "hfs-highlight": "#FBBF24",       # Highlight yellow
    },
)
