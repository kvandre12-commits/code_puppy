"""Register Android notification kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_notification_doctor as android_notification_doctor_impl,
    android_notification_send as android_notification_send_impl,
    android_notification_setup_guide as android_notification_setup_guide_impl,
    android_open_notification_settings as android_open_notification_settings_impl,
)

_DOCTOR = "android_notification_doctor"
_SETTINGS = "android_open_notification_settings"
_SETUP = "android_notification_setup_guide"
_SEND = "android_notification_send"



def register_android_notification_doctor(agent: Any) -> None:
    @agent.tool
    async def android_notification_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_notification_doctor_impl()



def register_android_open_notification_settings(agent: Any) -> None:
    @agent.tool
    async def android_open_notification_settings(context: RunContext) -> dict[str, Any]:
        del context
        return android_open_notification_settings_impl()



def register_android_notification_setup_guide(agent: Any) -> None:
    @agent.tool
    async def android_notification_setup_guide(context: RunContext) -> dict[str, Any]:
        del context
        return android_notification_setup_guide_impl()



def register_android_notification_send(agent: Any) -> None:
    @agent.tool
    async def android_notification_send(
        context: RunContext,
        text: str,
        title: str = "DroidPuppy",
        dry_run: bool = False,
        allow_share_fallback: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_notification_send_impl(
            text=text,
            title=title,
            dry_run=dry_run,
            allow_share_fallback=allow_share_fallback,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_notification_doctor},
        {"name": _SETTINGS, "register_func": register_android_open_notification_settings},
        {"name": _SETUP, "register_func": register_android_notification_setup_guide},
        {"name": _SEND, "register_func": register_android_notification_send},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _SETTINGS, _SETUP, _SEND]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
