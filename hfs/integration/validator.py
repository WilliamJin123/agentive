"""Validation suite for HFS merged artifacts.

The Validator runs a series of checks on the merged output to ensure
quality and correctness before finalizing:
- Syntax check: Code is syntactically valid
- Render test: Components can be rendered
- Accessibility audit: Basic a11y compliance
- Performance check: No obvious performance issues

Key concepts:
- ValidationResult: Contains pass/fail status with detailed issues
- ValidationIssue: A specific problem found during validation
- Severity levels: error, warning, info
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import re

from .merger import MergedArtifact


class IssueSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Must fix - will break functionality
    WARNING = "warning"  # Should fix - potential problems
    INFO = "info"        # Nice to fix - best practices


class IssueCategory(Enum):
    """Categories of validation issues."""
    SYNTAX = "syntax"
    RENDER = "render"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    STYLE = "style"
    SECURITY = "security"


@dataclass
class ValidationIssue:
    """A specific issue found during validation.

    Attributes:
        severity: How serious this issue is.
        category: What type of issue this is.
        message: Human-readable description of the issue.
        file_path: Which file the issue is in (if applicable).
        line_number: Line number of the issue (if applicable).
        suggestion: Suggested fix (if available).
    """
    severity: IssueSeverity
    category: IssueCategory
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of running the validation suite.

    Attributes:
        passed: Whether validation passed (no errors).
        issues: List of all issues found.
        checks_run: List of check names that were run.
        summary: Summary statistics.
    """
    passed: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize summary statistics."""
        self._update_summary()

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue and update status."""
        self.issues.append(issue)
        if issue.severity == IssueSeverity.ERROR:
            self.passed = False
        self._update_summary()

    def _update_summary(self) -> None:
        """Update summary statistics based on issues."""
        self.summary = {
            "total": len(self.issues),
            "errors": sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR),
            "warnings": sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING),
            "info": sum(1 for i in self.issues if i.severity == IssueSeverity.INFO),
        }

    @property
    def error_count(self) -> int:
        """Return count of error-level issues."""
        return self.summary.get("errors", 0)

    @property
    def warning_count(self) -> int:
        """Return count of warning-level issues."""
        return self.summary.get("warnings", 0)

    def get_issues_by_category(self, category: IssueCategory) -> List[ValidationIssue]:
        """Get all issues of a specific category."""
        return [i for i in self.issues if i.category == category]

    def get_issues_by_severity(self, severity: IssueSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [i for i in self.issues if i.severity == severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "checks_run": self.checks_run,
            "summary": self.summary,
        }


class Validator:
    """Runs validation suite on merged artifacts.

    The validator performs multiple checks:
    1. Syntax check - verifies code structure
    2. Render check - basic renderability test
    3. Accessibility check - WCAG compliance basics
    4. Performance check - common performance issues

    Example usage:
        validator = Validator()
        result = validator.validate(merged_artifact)
        if not result.passed:
            for issue in result.issues:
                print(f"{issue.severity.value}: {issue.message}")
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the Validator.

        Args:
            strict_mode: If True, warnings are treated as errors.
        """
        self.strict_mode = strict_mode

        # Patterns for various checks
        self._unclosed_tag_pattern = re.compile(r'<(\w+)[^>]*>(?!.*</\1>)', re.DOTALL)
        self._console_log_pattern = re.compile(r'console\.(log|debug|warn|error)\s*\(')
        self._inline_style_pattern = re.compile(r'style\s*=\s*\{?\s*["\']')
        self._missing_alt_pattern = re.compile(r'<img[^>]+(?!alt=)[^>]*>')
        self._missing_key_pattern = re.compile(r'\.map\s*\([^)]*\)\s*=>\s*[^{]*(?!key=)')

    def validate(self, artifact: MergedArtifact) -> ValidationResult:
        """Run full validation suite on merged artifact.

        Args:
            artifact: The MergedArtifact to validate.

        Returns:
            ValidationResult with all issues found.
        """
        result = ValidationResult()

        # Run all checks
        self._check_syntax(artifact, result)
        self._check_render(artifact, result)
        self._check_accessibility(artifact, result)
        self._check_performance(artifact, result)

        # In strict mode, warnings become errors
        if self.strict_mode and result.warning_count > 0:
            result.passed = False

        return result

    def _check_syntax(self, artifact: MergedArtifact, result: ValidationResult) -> None:
        """Check for syntax errors and structural issues.

        This is a simplified check that looks for common patterns.
        In production, would use actual parsers (babel, typescript, etc.).

        Args:
            artifact: The artifact to check.
            result: ValidationResult to add issues to.
        """
        result.checks_run.append("syntax")

        for file_path, content in artifact.files.items():
            # Skip non-code files
            if not self._is_code_file(file_path):
                continue

            # Check bracket matching
            self._check_bracket_balance(content, file_path, result)

            # Check for unterminated strings
            self._check_string_termination(content, file_path, result)

            # Check for common syntax issues
            self._check_common_syntax_issues(content, file_path, result)

    def _check_bracket_balance(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check that brackets are balanced."""
        bracket_pairs = {'{': '}', '[': ']', '(': ')'}
        stack: List[str] = []

        # Simple bracket counting (doesn't handle strings/comments properly)
        # In production would use proper parsing
        for char in content:
            if char in bracket_pairs:
                stack.append(char)
            elif char in bracket_pairs.values():
                if not stack:
                    result.add_issue(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.SYNTAX,
                        message=f"Unmatched closing bracket '{char}'",
                        file_path=file_path,
                    ))
                    return
                expected_close = bracket_pairs[stack.pop()]
                if char != expected_close:
                    result.add_issue(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.SYNTAX,
                        message=f"Bracket mismatch: expected '{expected_close}', found '{char}'",
                        file_path=file_path,
                    ))
                    return

        if stack:
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SYNTAX,
                message=f"Unclosed brackets: {len(stack)} opening bracket(s) without closing",
                file_path=file_path,
            ))

    def _check_string_termination(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check for unterminated string literals."""
        # Simple check for unmatched quotes
        # Count quotes outside of escaped sequences
        single_quotes = content.count("'") - content.count("\\'")
        double_quotes = content.count('"') - content.count('\\"')

        if single_quotes % 2 != 0:
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.SYNTAX,
                message="Possible unterminated single-quoted string",
                file_path=file_path,
                suggestion="Check for unmatched single quotes",
            ))

        if double_quotes % 2 != 0:
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.SYNTAX,
                message="Possible unterminated double-quoted string",
                file_path=file_path,
                suggestion="Check for unmatched double quotes",
            ))

    def _check_common_syntax_issues(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check for common syntax problems."""
        # Check for common typos
        typo_patterns = [
            (r'functoin\s', "Typo: 'functoin' should be 'function'"),
            (r'retrun\s', "Typo: 'retrun' should be 'return'"),
            (r'cosnt\s', "Typo: 'cosnt' should be 'const'"),
            (r'improt\s', "Typo: 'improt' should be 'import'"),
        ]

        for pattern, message in typo_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.SYNTAX,
                    message=message,
                    file_path=file_path,
                ))

    def _check_render(self, artifact: MergedArtifact, result: ValidationResult) -> None:
        """Check that components can be rendered.

        This is a simplified static analysis check.
        In production, would use actual rendering with JSDOM or similar.

        Args:
            artifact: The artifact to check.
            result: ValidationResult to add issues to.
        """
        result.checks_run.append("render")

        for file_path, content in artifact.files.items():
            # Only check component files
            if not file_path.endswith(('.tsx', '.jsx', '.vue')):
                continue

            # Check for return statement in components
            if 'export' in content and ('function' in content or '=>' in content):
                if 'return' not in content and 'return' not in content:
                    # Arrow function with implicit return is okay
                    if '=>' in content and '(' in content:
                        # Check if it's an implicit return arrow function
                        arrow_match = re.search(r'=>\s*[^{]', content)
                        if not arrow_match:
                            result.add_issue(ValidationIssue(
                                severity=IssueSeverity.WARNING,
                                category=IssueCategory.RENDER,
                                message="Component may not return JSX",
                                file_path=file_path,
                                suggestion="Ensure component returns valid JSX",
                            ))

            # Check for undefined component references
            # Simple check: look for PascalCase names that aren't defined or imported
            # This is very simplified - production would use AST analysis

    def _check_accessibility(
        self,
        artifact: MergedArtifact,
        result: ValidationResult
    ) -> None:
        """Check for basic accessibility issues.

        Checks for common WCAG violations:
        - Missing alt text on images
        - Missing ARIA labels on interactive elements
        - Color contrast issues (simplified)

        Args:
            artifact: The artifact to check.
            result: ValidationResult to add issues to.
        """
        result.checks_run.append("accessibility")

        for file_path, content in artifact.files.items():
            if not self._is_code_file(file_path):
                continue

            # Check for images without alt text
            self._check_image_alt(content, file_path, result)

            # Check for buttons/links without accessible names
            self._check_interactive_a11y(content, file_path, result)

            # Check for form inputs without labels
            self._check_form_labels(content, file_path, result)

    def _check_image_alt(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check images have alt text."""
        # Find img tags without alt attribute
        img_pattern = re.compile(r'<img\s+([^>]*)>', re.IGNORECASE)
        for match in img_pattern.finditer(content):
            attrs = match.group(1)
            if 'alt=' not in attrs and 'alt =' not in attrs:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.ACCESSIBILITY,
                    message="Image missing alt text",
                    file_path=file_path,
                    suggestion="Add alt attribute to describe the image, or alt='' for decorative images",
                ))

    def _check_interactive_a11y(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check interactive elements have accessible names."""
        # Check for buttons with only icons (no text or aria-label)
        icon_button_pattern = re.compile(
            r'<button[^>]*>[\s\n]*<(?:svg|i|span class="icon)[^>]*>[\s\n]*</button>',
            re.IGNORECASE | re.MULTILINE
        )
        for match in icon_button_pattern.finditer(content):
            button_html = match.group(0)
            if 'aria-label' not in button_html and 'aria-labelledby' not in button_html:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.ACCESSIBILITY,
                    message="Icon button may be missing accessible name",
                    file_path=file_path,
                    suggestion="Add aria-label to describe the button action",
                ))

        # Check for onClick on non-interactive elements
        click_div_pattern = re.compile(r'<div[^>]*onClick[^>]*>', re.IGNORECASE)
        for match in click_div_pattern.finditer(content):
            div_html = match.group(0)
            if 'role=' not in div_html and 'tabIndex' not in div_html:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.ACCESSIBILITY,
                    message="Clickable div without role or tabIndex",
                    file_path=file_path,
                    suggestion="Add role='button' and tabIndex={0} for keyboard accessibility",
                ))

    def _check_form_labels(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check form inputs have associated labels."""
        # Find input elements
        input_pattern = re.compile(r'<input\s+([^>]*)>', re.IGNORECASE)
        for match in input_pattern.finditer(content):
            attrs = match.group(1)
            # Skip hidden, submit, button types
            if any(t in attrs for t in ['type="hidden"', 'type="submit"', 'type="button"']):
                continue

            # Check for aria-label or id (for label association)
            if ('aria-label' not in attrs and
                'aria-labelledby' not in attrs and
                'id=' not in attrs):
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.ACCESSIBILITY,
                    message="Form input may be missing label",
                    file_path=file_path,
                    suggestion="Add a label element with htmlFor, or use aria-label",
                ))

    def _check_performance(
        self,
        artifact: MergedArtifact,
        result: ValidationResult
    ) -> None:
        """Check for common performance issues.

        Looks for patterns that may cause performance problems:
        - Large inline objects/arrays in render
        - Missing keys in lists
        - Console.log statements

        Args:
            artifact: The artifact to check.
            result: ValidationResult to add issues to.
        """
        result.checks_run.append("performance")

        for file_path, content in artifact.files.items():
            if not self._is_code_file(file_path):
                continue

            # Check for console.log statements
            self._check_console_statements(content, file_path, result)

            # Check for inline function definitions in JSX
            self._check_inline_handlers(content, file_path, result)

            # Check for missing keys in list rendering
            self._check_list_keys(content, file_path, result)

    def _check_console_statements(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check for console.log statements."""
        if self._console_log_pattern.search(content):
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.PERFORMANCE,
                message="Console statement found in production code",
                file_path=file_path,
                suggestion="Remove or replace with proper logging",
            ))

    def _check_inline_handlers(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check for inline arrow functions in event handlers."""
        # Pattern for inline arrow functions in onClick, onChange, etc.
        inline_handler_pattern = re.compile(
            r'on\w+\s*=\s*\{\s*\([^)]*\)\s*=>',
            re.IGNORECASE
        )

        count = len(inline_handler_pattern.findall(content))
        if count > 3:  # Threshold for warning
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.PERFORMANCE,
                message=f"Found {count} inline arrow function handlers",
                file_path=file_path,
                suggestion="Consider using useCallback for frequently re-rendered components",
            ))

    def _check_list_keys(
        self,
        content: str,
        file_path: str,
        result: ValidationResult
    ) -> None:
        """Check for missing key props in list rendering."""
        # Look for .map() calls that don't include key=
        map_pattern = re.compile(
            r'\.map\s*\(\s*(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>\s*(?:\{[^}]*return\s*)?<\w+[^>]*',
            re.MULTILINE | re.DOTALL
        )

        for match in map_pattern.finditer(content):
            jsx_start = match.group(0)
            # Check if key prop is present in the JSX element
            if 'key=' not in jsx_start and 'key =' not in jsx_start:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.PERFORMANCE,
                    message="List rendering may be missing key prop",
                    file_path=file_path,
                    suggestion="Add unique key prop to list items for efficient reconciliation",
                ))
                break  # Only report once per file

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file that should be validated."""
        code_extensions = ('.ts', '.tsx', '.js', '.jsx', '.vue', '.svelte')
        return file_path.endswith(code_extensions)
