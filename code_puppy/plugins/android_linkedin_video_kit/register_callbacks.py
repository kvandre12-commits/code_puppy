"""Register LinkedIn video verification tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_linkedin_video_doctor as android_linkedin_video_doctor_impl,
    android_linkedin_video_plan as android_linkedin_video_plan_impl,
    android_linkedin_video_run as android_linkedin_video_run_impl,
)

_DOCTOR = "android_linkedin_video_doctor"
_PLAN = "android_linkedin_video_plan"
_RUN = "android_linkedin_video_run"


def register_android_linkedin_video_doctor(agent: Any) -> None:
    @agent.tool
    async def android_linkedin_video_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_linkedin_video_doctor_impl()


def register_android_linkedin_video_plan(agent: Any) -> None:
    @agent.tool
    async def android_linkedin_video_plan(
        context: RunContext,
        post_hint: str = "today's LinkedIn video",
    ) -> dict[str, Any]:
        del context
        return android_linkedin_video_plan_impl(post_hint=post_hint)


def register_android_linkedin_video_run(agent: Any) -> None:
    @agent.tool
    async def android_linkedin_video_run(
        context: RunContext,
        post_hint: str = "today's LinkedIn video",
        dry_run: bool = True,
        record_seconds: int = 12,
        launch_app: bool = True,
        require_adb: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_linkedin_video_run_impl(
            post_hint=post_hint,
            dry_run=dry_run,
            record_seconds=record_seconds,
            launch_app=launch_app,
            require_adb=require_adb,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_linkedin_video_doctor},
        {"name": _PLAN, "register_func": register_android_linkedin_video_plan},
        {"name": _RUN, "register_func": register_android_linkedin_video_run},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _PLAN, _RUN]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
