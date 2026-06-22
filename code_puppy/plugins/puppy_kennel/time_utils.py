"""Tiny timestamp helpers for puppy_kennel."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Return the current UTC timestamp in second precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
