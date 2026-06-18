"""Context hygiene rules for Puppy Kennel ingestion.

The kennel is a local context cache, not a junk drawer. Passive autosave should
only keep responses likely to help future working-context reconstruction.
Explicit notes are trusted more, but still get duplicate protection.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import MIN_DRAWER_CHARS

# Passive assistant transcript capture is noisier than explicit notes, so it
# uses the same floor as prompt packing. If it would never be packed, don't store
# it in the first place. Explicit `kennel_remember` notes are exempt.
AUTOSAVE_MIN_CHARS = MIN_DRAWER_CHARS

_PLACEHOLDER_RESPONSES = frozenset(
    {
        "response",
        "reused response",
        "assistant response",
        "model response",
    }
)


@dataclass(frozen=True, slots=True)
class HygieneDecision:
    """Whether content should be stored and why."""

    should_store: bool
    reason: str = "ok"


def normalize_content(content: str) -> str:
    """Collapse whitespace for duplicate/noise checks."""
    return " ".join((content or "").split())


def autosave_decision(content: str) -> HygieneDecision:
    """Decide whether a passive assistant response deserves storage."""
    normalized = normalize_content(content)
    if not normalized:
        return HygieneDecision(False, "blank")
    if normalized.lower() in _PLACEHOLDER_RESPONSES:
        return HygieneDecision(False, "placeholder")
    if len(normalized) < AUTOSAVE_MIN_CHARS:
        return HygieneDecision(False, "too_short")
    return HygieneDecision(True)
