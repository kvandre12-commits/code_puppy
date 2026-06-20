"""Register Android input kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_input_doctor as android_input_doctor_impl,
    android_input_keyevent as android_input_keyevent_impl,
    android_input_swipe as android_input_swipe_impl,
    android_input_tap as android_input_tap_impl,
    android_input_tap_bounds as android_input_tap_bounds_impl,
    android_input_text as android_input_text_impl,
)

_DOCTOR = "android_input_doctor"
_TAP = "android_input_tap"
_TAP_BOUNDS = "android_input_tap_bounds"
_SWIPE = "android_input_swipe"
_TEXT = "android_input_text"
_KEYEVENT = "android_input_keyevent"


def register_android_input_doctor(agent: Any) -> None:
    @agent.tool
    async def android_input_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_input_doctor_impl()


def register_android_input_tap(agent: Any) -> None:
    @agent.tool
    async def android_input_tap(
        context: RunContext,
        x: int,
        y: int,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_input_tap_impl(x=x, y=y, dry_run=dry_run)


def register_android_input_tap_bounds(agent: Any) -> None:
    @agent.tool
    async def android_input_tap_bounds(
        context: RunContext,
        bounds: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_input_tap_bounds_impl(bounds=bounds, dry_run=dry_run)


def register_android_input_swipe(agent: Any) -> None:
    @agent.tool
    async def android_input_swipe(
        context: RunContext,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_input_swipe_impl(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            duration_ms=duration_ms,
            dry_run=dry_run,
        )


def register_android_input_text(agent: Any) -> None:
    @agent.tool
    async def android_input_text(
        context: RunContext,
        text: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_input_text_impl(text=text, dry_run=dry_run)


def register_android_input_keyevent(agent: Any) -> None:
    @agent.tool
    async def android_input_keyevent(
        context: RunContext,
        keycode: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_input_keyevent_impl(keycode=keycode, dry_run=dry_run)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_input_doctor},
        {"name": _TAP, "register_func": register_android_input_tap},
        {"name": _TAP_BOUNDS, "register_func": register_android_input_tap_bounds},
        {"name": _SWIPE, "register_func": register_android_input_swipe},
        {"name": _TEXT, "register_func": register_android_input_text},
        {"name": _KEYEVENT, "register_func": register_android_input_keyevent},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _TAP, _TAP_BOUNDS, _SWIPE, _TEXT, _KEYEVENT]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
