"""Register Android screen capture kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_capture_screenshot as android_capture_screenshot_impl,
    android_record_screen as android_record_screen_impl,
    android_screen_capture_doctor as android_screen_capture_doctor_impl,
)

_DOCTOR = "android_screen_capture_doctor"
_SCREENSHOT = "android_capture_screenshot"
_RECORD = "android_record_screen"



def register_android_screen_capture_doctor(agent: Any) -> None:
    @agent.tool
    async def android_screen_capture_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_screen_capture_doctor_impl()



def register_android_capture_screenshot(agent: Any) -> None:
    @agent.tool
    async def android_capture_screenshot(
        context: RunContext,
        artifact_name: str = "android_screen",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        del context
        return android_capture_screenshot_impl(
            artifact_name=artifact_name,
            dry_run=dry_run,
        )



def register_android_record_screen(agent: Any) -> None:
    @agent.tool
    async def android_record_screen(
        context: RunContext,
        seconds: int = 10,
        artifact_name: str = "android_screen_recording",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        del context
        return android_record_screen_impl(
            seconds=seconds,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_screen_capture_doctor},
        {"name": _SCREENSHOT, "register_func": register_android_capture_screenshot},
        {"name": _RECORD, "register_func": register_android_record_screen},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _SCREENSHOT, _RECORD]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
