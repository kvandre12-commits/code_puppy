"""Effect-owned argument validation for Project runtime preflight."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from . import effect_specs

ALLOWED_BROWSER_URL = "https://example.com/"
APPROVED_ANDROID_COMPONENT = "com.android.settings/.Settings"

ArgumentValidator = Callable[[Mapping[str, Any]], tuple[str, ...]]


def _text(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments.get(name, "")
    return value.strip() if isinstance(value, str) else str(value).strip()


def _validate_noop(_arguments: Mapping[str, Any]) -> tuple[str, ...]:
    return ()


def _validate_browser(arguments: Mapping[str, Any]) -> tuple[str, ...]:
    if _text(arguments, "url") != ALLOWED_BROWSER_URL:
        return ("browser URL scope mismatch",)
    return ()


def _validate_android(arguments: Mapping[str, Any]) -> tuple[str, ...]:
    if _text(arguments, "component") != APPROVED_ANDROID_COMPONENT:
        return ("Android activity scope mismatch",)
    return ()


def _validate_memory_recall(arguments: Mapping[str, Any]) -> tuple[str, ...]:
    if not _text(arguments, "query"):
        return ("query missing",)
    return ()


def _validate_memory_promote(arguments: Mapping[str, Any]) -> tuple[str, ...]:
    blockers: list[str] = []
    if not _text(arguments, "source_evidence"):
        blockers.append("source evidence missing")
    if not _text(arguments, "mutation_reason"):
        blockers.append("mutation reason missing")
    if not _text(arguments, "proposed_after_object"):
        blockers.append("proposed after object missing")
    return tuple(blockers)


_VALIDATORS: dict[str, ArgumentValidator] = {
    effect_specs.NOOP.name: _validate_noop,
    effect_specs.BROWSER.name: _validate_browser,
    effect_specs.ANDROID.name: _validate_android,
    effect_specs.MEMORY_RECALL.name: _validate_memory_recall,
    effect_specs.MEMORY_PROMOTE.name: _validate_memory_promote,
}


def blockers_for_effect_arguments(
    effect: effect_specs.EffectSpec,
    arguments: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return adapter-owned blockers for normalized proposed arguments."""
    try:
        validator = _VALIDATORS[effect.name]
    except KeyError:
        return (f"effect adapter unavailable: {effect.name}",)
    return validator(arguments)
