"""Test rendering for HFS merged artifacts.

The TestRenderer provides a simple rendering mechanism for testing
and previewing merged artifacts without requiring a full browser environment.

Key concepts:
- RenderResult: Contains rendered output and any errors
- TestRenderer: Simulates rendering for validation purposes
- Render modes: static HTML, component tree, screenshot (stubbed)

This is a simplified implementation suitable for testing.
Production rendering would use actual browser/JSDOM environments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import re
import html

from .merger import MergedArtifact


class RenderMode(Enum):
    """Available rendering modes."""
    STATIC_HTML = "static_html"       # Generate static HTML
    COMPONENT_TREE = "component_tree"  # Generate component hierarchy
    TEXT_ONLY = "text_only"           # Extract text content only


class RenderStatus(Enum):
    """Status of a render operation."""
    SUCCESS = "success"
    PARTIAL = "partial"   # Rendered with some issues
    FAILED = "failed"     # Could not render


@dataclass
class RenderError:
    """An error that occurred during rendering.

    Attributes:
        component: Name of the component that failed.
        message: Error message.
        recoverable: Whether rendering can continue.
    """
    component: str
    message: str
    recoverable: bool = True


@dataclass
class ComponentNode:
    """A node in the rendered component tree.

    Attributes:
        name: Component name.
        props: Props passed to the component.
        children: Child component nodes.
        source_file: Source file path.
    """
    name: str
    props: Dict[str, Any] = field(default_factory=dict)
    children: List['ComponentNode'] = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "props": self.props,
            "children": [c.to_dict() for c in self.children],
            "source_file": self.source_file,
        }

    def to_ascii_tree(self, indent: int = 0) -> str:
        """Generate ASCII tree representation."""
        prefix = "  " * indent
        result = f"{prefix}{self.name}"
        if self.props:
            props_str = ", ".join(f"{k}={v}" for k, v in list(self.props.items())[:3])
            result += f" ({props_str})"
        result += "\n"
        for child in self.children:
            result += child.to_ascii_tree(indent + 1)
        return result


@dataclass
class RenderResult:
    """Result of rendering a merged artifact.

    Attributes:
        status: Overall render status.
        mode: Which render mode was used.
        output: The rendered output (varies by mode).
        component_tree: Component hierarchy (if mode is COMPONENT_TREE).
        html: Static HTML output (if mode is STATIC_HTML).
        text_content: Extracted text (if mode is TEXT_ONLY).
        errors: List of errors encountered.
        warnings: List of warnings.
        render_time_ms: Time taken to render in milliseconds.
    """
    status: RenderStatus = RenderStatus.SUCCESS
    mode: RenderMode = RenderMode.STATIC_HTML
    output: Any = None
    component_tree: Optional[ComponentNode] = None
    html: Optional[str] = None
    text_content: Optional[str] = None
    errors: List[RenderError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    render_time_ms: float = 0.0

    def add_error(self, error: RenderError) -> None:
        """Add an error and update status."""
        self.errors.append(error)
        if not error.recoverable:
            self.status = RenderStatus.FAILED
        elif self.status == RenderStatus.SUCCESS:
            self.status = RenderStatus.PARTIAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "mode": self.mode.value,
            "html": self.html,
            "text_content": self.text_content,
            "component_tree": self.component_tree.to_dict() if self.component_tree else None,
            "errors": [{"component": e.component, "message": e.message} for e in self.errors],
            "warnings": self.warnings,
            "render_time_ms": self.render_time_ms,
        }


class TestRenderer:
    """Simulates rendering for testing and validation.

    The TestRenderer provides lightweight rendering simulation without
    requiring a full browser environment. It's useful for:
    - Validating component structure
    - Extracting text content for testing
    - Generating static HTML previews
    - Building component trees for analysis

    Example usage:
        renderer = TestRenderer()
        result = renderer.render(merged_artifact)
        if result.status == RenderStatus.SUCCESS:
            print(result.html)
    """

    def __init__(
        self,
        mode: RenderMode = RenderMode.STATIC_HTML,
        include_styles: bool = True
    ) -> None:
        """Initialize the TestRenderer.

        Args:
            mode: Default rendering mode to use.
            include_styles: Whether to include styles in HTML output.
        """
        self.default_mode = mode
        self.include_styles = include_styles

        # Patterns for extracting component information
        self._component_pattern = re.compile(
            r'(?:export\s+)?(?:default\s+)?(?:function|const)\s+(\w+)\s*'
            r'(?::\s*\w+(?:<[^>]+>)?)?\s*[=(]',
            re.MULTILINE
        )
        self._jsx_element_pattern = re.compile(
            r'<(\w+)([^>]*)(?:/>|>)',
            re.MULTILINE
        )
        self._prop_pattern = re.compile(
            r'(\w+)\s*=\s*(?:\{([^}]+)\}|"([^"]+)"|\'([^\']+)\')',
        )

    def render(
        self,
        artifact: MergedArtifact,
        mode: Optional[RenderMode] = None,
        entry_component: Optional[str] = None
    ) -> RenderResult:
        """Render the merged artifact.

        Args:
            artifact: The MergedArtifact to render.
            mode: Render mode to use (defaults to instance default).
            entry_component: Specific component to render (default: all).

        Returns:
            RenderResult with rendered output.
        """
        import time
        start_time = time.time()

        render_mode = mode or self.default_mode
        result = RenderResult(mode=render_mode)

        if not artifact.files:
            result.add_error(RenderError(
                component="root",
                message="No files in artifact to render",
                recoverable=False,
            ))
            return result

        try:
            if render_mode == RenderMode.STATIC_HTML:
                self._render_static_html(artifact, result, entry_component)
            elif render_mode == RenderMode.COMPONENT_TREE:
                self._render_component_tree(artifact, result, entry_component)
            elif render_mode == RenderMode.TEXT_ONLY:
                self._render_text_only(artifact, result)
        except Exception as e:
            result.add_error(RenderError(
                component="root",
                message=f"Render exception: {str(e)}",
                recoverable=False,
            ))

        result.render_time_ms = (time.time() - start_time) * 1000
        return result

    def _render_static_html(
        self,
        artifact: MergedArtifact,
        result: RenderResult,
        entry_component: Optional[str]
    ) -> None:
        """Generate static HTML representation.

        Args:
            artifact: The artifact to render.
            result: RenderResult to populate.
            entry_component: Optional specific component to render.
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "  <meta charset='UTF-8'>",
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "  <title>HFS Render Preview</title>",
        ]

        # Include styles if requested
        if self.include_styles and artifact.style_bundle:
            html_parts.append("  <style>")
            html_parts.append(f"    {html.escape(artifact.style_bundle)}")
            html_parts.append("  </style>")

        html_parts.extend([
            "</head>",
            "<body>",
            "  <div id='root'>",
        ])

        # Extract and convert JSX to HTML
        components_rendered = 0
        for file_path, content in artifact.files.items():
            if not file_path.endswith(('.tsx', '.jsx')):
                continue

            # Extract component names
            component_names = self._component_pattern.findall(content)
            if entry_component and entry_component not in component_names:
                continue

            for comp_name in component_names:
                if entry_component and comp_name != entry_component:
                    continue

                # Try to extract JSX content
                jsx_html = self._jsx_to_html(content, comp_name)
                if jsx_html:
                    html_parts.append(f"    <!-- Component: {comp_name} from {file_path} -->")
                    html_parts.append(f"    <div class='component-{comp_name.lower()}'>")
                    html_parts.append(f"      {jsx_html}")
                    html_parts.append("    </div>")
                    components_rendered += 1

        if components_rendered == 0:
            result.warnings.append("No components could be rendered to HTML")
            html_parts.append("    <p>No components rendered</p>")

        html_parts.extend([
            "  </div>",
            "</body>",
            "</html>",
        ])

        result.html = "\n".join(html_parts)
        result.output = result.html

    def _jsx_to_html(self, content: str, component_name: str) -> Optional[str]:
        """Convert JSX to static HTML (simplified).

        This is a very basic conversion that handles simple cases.
        Production would use a proper JSX parser.

        Args:
            content: The file content.
            component_name: Name of the component.

        Returns:
            HTML string or None if conversion failed.
        """
        # Find the return statement of the component
        # This is a simplified approach that won't work for all cases
        return_pattern = re.compile(
            rf'{component_name}[^{{]*\{{[^}}]*return\s*\(([^)]+)\)',
            re.DOTALL | re.MULTILINE
        )

        match = return_pattern.search(content)
        if not match:
            # Try arrow function implicit return
            arrow_pattern = re.compile(
                rf'{component_name}[^=]*=\s*[^=]*=>\s*\(([^)]+)\)',
                re.DOTALL | re.MULTILINE
            )
            match = arrow_pattern.search(content)

        if not match:
            return None

        jsx = match.group(1).strip()

        # Convert JSX to HTML (simplified)
        # Replace className with class
        html_str = re.sub(r'className\s*=', 'class=', jsx)

        # Remove JS expressions in curly braces (replace with placeholder)
        html_str = re.sub(r'\{[^}]+\}', '[dynamic]', html_str)

        # Self-closing tags
        html_str = re.sub(r'<(\w+)([^>]*)/>', r'<\1\2></\1>', html_str)

        return html_str

    def _render_component_tree(
        self,
        artifact: MergedArtifact,
        result: RenderResult,
        entry_component: Optional[str]
    ) -> None:
        """Build component tree representation.

        Args:
            artifact: The artifact to render.
            result: RenderResult to populate.
            entry_component: Optional specific component to render.
        """
        root = ComponentNode(name="Root", source_file=None)

        for file_path, content in artifact.files.items():
            if not file_path.endswith(('.tsx', '.jsx')):
                continue

            # Find component definitions
            components = self._extract_components(content, file_path)

            for comp in components:
                if entry_component and comp.name != entry_component:
                    continue
                root.children.append(comp)

        result.component_tree = root
        result.output = root.to_ascii_tree()

    def _extract_components(
        self,
        content: str,
        file_path: str
    ) -> List[ComponentNode]:
        """Extract component nodes from file content.

        Args:
            content: File content.
            file_path: Source file path.

        Returns:
            List of ComponentNode objects.
        """
        components: List[ComponentNode] = []

        # Find component definitions
        for match in self._component_pattern.finditer(content):
            comp_name = match.group(1)

            # Extract props from the component signature
            props = self._extract_component_props(content, comp_name)

            # Extract child components from JSX
            children = self._extract_jsx_children(content, comp_name)

            components.append(ComponentNode(
                name=comp_name,
                props=props,
                children=children,
                source_file=file_path,
            ))

        return components

    def _extract_component_props(
        self,
        content: str,
        component_name: str
    ) -> Dict[str, Any]:
        """Extract props definition from component.

        Args:
            content: File content.
            component_name: Name of the component.

        Returns:
            Dict of prop names to their types/values.
        """
        # Look for props interface or type
        props_pattern = re.compile(
            rf'(?:interface|type)\s+{component_name}Props\s*[=]?\s*\{{([^}}]+)\}}',
            re.MULTILINE
        )

        match = props_pattern.search(content)
        if match:
            props_body = match.group(1)
            props = {}
            for line in props_body.split(';'):
                line = line.strip()
                if ':' in line:
                    parts = line.split(':')
                    prop_name = parts[0].strip().rstrip('?')
                    prop_type = parts[1].strip() if len(parts) > 1 else 'any'
                    props[prop_name] = prop_type
            return props

        return {}

    def _extract_jsx_children(
        self,
        content: str,
        component_name: str
    ) -> List[ComponentNode]:
        """Extract child component references from JSX.

        Args:
            content: File content.
            component_name: Name of the parent component.

        Returns:
            List of child ComponentNode references.
        """
        children: List[ComponentNode] = []

        # Find the component's render/return content
        render_pattern = re.compile(
            rf'{component_name}[^{{]*\{{.*?return\s*\(([^)]+)\)',
            re.DOTALL
        )

        match = render_pattern.search(content)
        if not match:
            return children

        jsx_content = match.group(1)

        # Find component references (PascalCase elements)
        component_refs = re.findall(r'<([A-Z]\w+)', jsx_content)

        for ref in set(component_refs):
            # Extract props passed to this child
            child_props = {}
            prop_match = re.search(
                rf'<{ref}\s+([^>]+)>',
                jsx_content
            )
            if prop_match:
                props_str = prop_match.group(1)
                for prop_match in self._prop_pattern.finditer(props_str):
                    prop_name = prop_match.group(1)
                    prop_value = (
                        prop_match.group(2) or
                        prop_match.group(3) or
                        prop_match.group(4)
                    )
                    child_props[prop_name] = prop_value

            children.append(ComponentNode(
                name=ref,
                props=child_props,
            ))

        return children

    def _render_text_only(
        self,
        artifact: MergedArtifact,
        result: RenderResult
    ) -> None:
        """Extract text content only.

        Args:
            artifact: The artifact to render.
            result: RenderResult to populate.
        """
        text_parts: List[str] = []

        for file_path, content in artifact.files.items():
            if not file_path.endswith(('.tsx', '.jsx', '.html')):
                continue

            # Extract text from JSX/HTML
            # Remove JSX expressions
            text = re.sub(r'\{[^}]+\}', '', content)

            # Remove HTML/JSX tags
            text = re.sub(r'<[^>]+>', '', text)

            # Remove import/export statements
            text = re.sub(r'^(?:import|export).*$', '', text, flags=re.MULTILINE)

            # Remove function/const declarations
            text = re.sub(r'^(?:function|const|let|var).*$', '', text, flags=re.MULTILINE)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            if text:
                text_parts.append(f"[{file_path}]")
                text_parts.append(text)
                text_parts.append("")

        result.text_content = "\n".join(text_parts)
        result.output = result.text_content

    def render_component(
        self,
        artifact: MergedArtifact,
        component_name: str
    ) -> RenderResult:
        """Render a specific component.

        Convenience method for rendering a single component.

        Args:
            artifact: The artifact containing the component.
            component_name: Name of the component to render.

        Returns:
            RenderResult for the specific component.
        """
        return self.render(artifact, entry_component=component_name)

    def get_component_list(self, artifact: MergedArtifact) -> List[str]:
        """Get list of all components in the artifact.

        Args:
            artifact: The artifact to scan.

        Returns:
            List of component names.
        """
        components: List[str] = []

        for file_path, content in artifact.files.items():
            if not file_path.endswith(('.tsx', '.jsx')):
                continue

            for match in self._component_pattern.finditer(content):
                components.append(match.group(1))

        return sorted(set(components))
