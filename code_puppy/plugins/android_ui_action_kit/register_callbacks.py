"""Register Android UI action kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_ui_action_doctor as android_ui_action_doctor_impl,
    android_ui_tap_match as android_ui_tap_match_impl,
    android_ui_text_into_match as android_ui_text_into_match_impl,
)

_DOCTOR = "android_ui_action_doctor"
_TAP_MATCH = "android_ui_tap_match"
_TEXT_MATCH = "android_ui_text_into_match"


def register_android_ui_action_doctor(agent: Any) -> None:
    @agent.tool
    async def android_ui_action_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_ui_action_doctor_impl()


def register_android_ui_tap_match(agent: Any) -> None:
    @agent.tool
    async def android_ui_tap_match(
        context: RunContext,
        query: str = "",
        resource_id: str = "",
        class_name: str = "",
        clickable_only: bool = True,
        match_index: int = 0,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_ui_tap_match_impl(
            query=query,
            resource_id=resource_id,
            class_name=class_name,
            clickable_only=clickable_only,
            match_index=match_index,
            dry_run=dry_run,
        )


def register_android_ui_text_into_match(agent: Any) -> None:
    @agent.tool
    async def android_ui_text_into_match(
        context: RunContext,
        value: str,
        query: str = "",
        resource_id: str = "",
        class_name: str = "",
        clickable_only: bool = False,
        match_index: int = 0,
        dry_run: bool = True,
        submit: bool = False,
    ) -> dict[str, Any]:
        del context
        return android_ui_text_into_match_impl(
            value=value,
            query=query,
            resource_id=resource_id,
            class_name=class_name,
            clickable_only=clickable_only,
            match_index=match_index,
            dry_run=dry_run,
            submit=submit,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_ui_action_doctor},
        {"name": _TAP_MATCH, "register_func": register_android_ui_tap_match},
        {"name": _TEXT_MATCH, "register_func": register_android_ui_text_into_match},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _TAP_MATCH, _TEXT_MATCH]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
