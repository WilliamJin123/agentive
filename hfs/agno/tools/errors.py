"""Error formatting utilities for HFS tools.

Provides LLM-friendly error responses that enable agent self-correction.
ValidationError produces retry-friendly hints; RuntimeError indicates
non-recoverable failures.
"""

from pydantic import ValidationError
import json
from typing import List


def format_validation_error(error: ValidationError) -> str:
    """Convert ValidationError to LLM-friendly JSON with hints.

    Produces a structured error response that helps the agent
    understand what went wrong and how to fix it.

    Args:
        error: Pydantic ValidationError from input validation

    Returns:
        JSON string with success=False, hints array, and retry_allowed=True
    """
    hints: List[str] = []
    for err in error.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        hints.append(f"{field}: {msg}")

    return json.dumps({
        "success": False,
        "error": "validation_error",
        "message": "Invalid input. Please fix and retry.",
        "hints": hints,
        "retry_allowed": True,
    })


def format_runtime_error(error: Exception, context: str = "") -> str:
    """Convert runtime errors to non-retryable JSON response.

    Runtime errors represent failures that cannot be fixed by
    retrying with different input (e.g., spec frozen, not owner).

    Args:
        error: The exception that occurred
        context: Additional context about what operation failed

    Returns:
        JSON string with success=False and retry_allowed=False
    """
    return json.dumps({
        "success": False,
        "error": "runtime_error",
        "message": str(error),
        "context": context,
        "retry_allowed": False,
    })
