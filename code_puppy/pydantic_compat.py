"""Small compatibility helpers for supported pydantic-ai runtimes."""

from collections.abc import Callable
from typing import Any

try:
    from pydantic_ai.capabilities import ProcessHistory as _ProcessHistory
except ImportError:  # pydantic-ai 1.56 and other pre-capability releases
    _ProcessHistory = None


def history_processor_kwargs(*processors: Callable[..., Any]) -> dict[str, Any]:
    """Return agent kwargs for ordered history processing.

    Newer pydantic-ai releases model history processors as capabilities, while
    the Android-safe locked release still requires ``history_processors``.
    Keep that version difference isolated here instead of spreading checks
    across every agent constructor.
    """
    if _ProcessHistory is None:
        return {"history_processors": list(processors)}

    return {
        "capabilities": [_ProcessHistory(processor) for processor in processors],
    }
