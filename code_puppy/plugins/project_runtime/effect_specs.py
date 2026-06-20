"""Governed effect scope registry for Project OS runtime commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EffectSpec:
    """Authority and capability scopes required for one effect adapter."""

    name: str
    action_scope: str
    capability_scope: str
    description: str


NOOP = EffectSpec(
    name="noop",
    action_scope="project_run.execute_bounded_step",
    capability_scope="project_runtime.step",
    description="harmless no-op runtime proof",
)

BROWSER = EffectSpec(
    name="browser",
    action_scope="browser.open_url",
    capability_scope="browser.url.example_com",
    description="bounded browser URL open",
)

ANDROID = EffectSpec(
    name="android",
    action_scope="android.launch_activity",
    capability_scope="android.activity.settings",
    description="bounded Android settings activity launch",
)

DEFAULT_EFFECT = NOOP.name

_EFFECTS = {
    NOOP.name: NOOP,
    BROWSER.name: BROWSER,
    ANDROID.name: ANDROID,
}


def get_effect_spec(name: str = DEFAULT_EFFECT) -> EffectSpec:
    """Return a known effect spec or raise a clear operator-facing error."""
    normalized = (name or DEFAULT_EFFECT).strip().lower()
    try:
        return _EFFECTS[normalized]
    except KeyError as exc:
        choices = ", ".join(sorted(_EFFECTS))
        raise ValueError(
            f"unknown effect '{name}'; expected one of: {choices}"
        ) from exc


def choices_text() -> str:
    """Return supported effect names for help text."""
    return "|".join(sorted(_EFFECTS))
