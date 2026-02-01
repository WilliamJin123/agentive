"""Agent tree widget for HFS TUI.

This module provides the AgentTreeWidget, a custom Tree widget for displaying
the hierarchical structure of agents in triads. Each agent node shows status
icons, triad-colored styling, and optional streaming indicators.

Usage:
    from hfs.tui.widgets import AgentTreeWidget
    from hfs.state.models import AgentTree, TriadInfo, AgentNode, AgentStatus

    tree_widget = AgentTreeWidget("Agents")
    tree_widget.populate_from_tree(agent_tree_model)
"""

from textual.reactive import reactive
from textual.widgets import Tree
from textual.widgets._tree import TreeNode
from rich.text import Text
from rich.style import Style

from hfs.state.models import AgentNode, AgentStatus, AgentTree, TriadInfo


class AgentTreeWidget(Tree[AgentNode]):
    """Tree widget for displaying agent hierarchy with live status.

    Displays agents organized by triad with custom node rendering that shows
    status icons, triad-specific colors, token counts, and streaming indicators.

    Attributes:
        is_live: Reactive boolean for live update toggle (default True).

    CSS Variables Used:
        $hfs-hierarchical: Blue color for hierarchical triads
        $hfs-dialectic: Purple color for dialectic triads
        $hfs-consensus: Green color for consensus triads
    """

    DEFAULT_CSS = """
    AgentTreeWidget {
        height: 100%;
        padding: 1;
        scrollbar-gutter: stable;
    }

    AgentTreeWidget > .tree--guides {
        color: #404040;
    }

    AgentTreeWidget > .tree--cursor {
        background: $surface;
    }
    """

    # Triad color mapping using theme variable names
    TRIAD_COLORS = {
        "hierarchical": "#3B82F6",  # Blue
        "dialectic": "#A855F7",  # Purple
        "consensus": "#22C55E",  # Green
    }

    # Status icons (Unicode from RESEARCH.md)
    STATUS_ICONS = {
        AgentStatus.IDLE: "\u25cb",  # Empty circle
        AgentStatus.WORKING: "\u25b6",  # Play
        AgentStatus.BLOCKED: "\u23f8",  # Pause
        AgentStatus.COMPLETE: "\u2713",  # Check
    }

    is_live: reactive[bool] = reactive(True)

    def __init__(self, label: str = "Agents", **kwargs) -> None:
        """Initialize the AgentTreeWidget.

        Args:
            label: Root node label for the tree.
            **kwargs: Additional arguments passed to Tree.
        """
        super().__init__(label, **kwargs)
        self._triad_presets: dict[str, str] = {}  # triad_id -> preset

    def render_label(
        self,
        node: TreeNode[AgentNode],
        base_style: Style,
        style: Style,
    ) -> Text:
        """Render a custom label for each tree node.

        Displays agent nodes with:
        - Status icon in triad color
        - Role name in bold triad color
        - Token count in dim text (if available)
        - Blinking "..." if agent is streaming

        Args:
            node: The tree node being rendered.
            base_style: Base style from the tree.
            style: Current computed style.

        Returns:
            Rich Text object for the node label.
        """
        agent = node.data
        if agent is None:
            # Non-agent node (root or triad header)
            return Text(str(node.label))

        # Get triad preset for coloring
        preset = self._triad_presets.get(agent.triad_id, "hierarchical")
        color = self.TRIAD_COLORS.get(preset, "#FFFFFF")

        # Status icon
        icon = self.STATUS_ICONS.get(agent.status, "\u25cb")

        # Build the label
        label = Text()
        label.append(icon, style=f"bold {color}")
        label.append(" ")
        label.append(agent.role, style=f"bold {color}")

        # Token count (check for token usage attribute if extended)
        if hasattr(agent, "token_count") and getattr(agent, "token_count", None):
            token_count = getattr(agent, "token_count")
            label.append(f" {token_count:,}", style="dim")

        # Streaming indicator with blink effect
        if hasattr(agent, "is_streaming") and getattr(agent, "is_streaming", False):
            label.append(" ...", style=f"blink {color}")
        elif agent.status == AgentStatus.WORKING:
            # If working but no is_streaming attr, show blinking dots
            label.append(" ...", style=f"blink {color}")

        return label

    def populate_from_tree(self, agent_tree: AgentTree) -> None:
        """Populate the tree widget from an AgentTree model.

        Clears existing nodes and rebuilds the tree structure with:
        - Expandable triad nodes showing "Triad: {preset}"
        - Leaf nodes for each agent within a triad
        - Auto-expands triads with active (WORKING) agents

        Args:
            agent_tree: The AgentTree model containing triads and agents.
        """
        # Clear existing nodes
        self.clear()
        self._triad_presets.clear()

        # Build tree structure
        for triad in agent_tree.triads:
            # Store preset for color lookup
            self._triad_presets[triad.triad_id] = triad.preset

            # Add triad as expandable node
            triad_label = f"Triad: {triad.preset}"
            triad_node = self.root.add(triad_label, expand=False)

            # Track if any agent is working (for auto-expand)
            has_active = False

            # Add agents as leaf nodes
            for agent in triad.agents:
                triad_node.add_leaf(agent.role, data=agent)
                if agent.status == AgentStatus.WORKING:
                    has_active = True

            # Auto-expand triads with active agents
            if has_active:
                triad_node.expand()


__all__ = ["AgentTreeWidget"]
