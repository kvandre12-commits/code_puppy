"""Register DroidPuppy support bundle tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_support_bundle_collect as android_support_bundle_collect_impl,
    android_support_bundle_doctor as android_support_bundle_doctor_impl,
    android_support_bundle_plan as android_support_bundle_plan_impl,
)

_DOCTOR = "android_support_bundle_doctor"
_PLAN = "android_support_bundle_plan"
_COLLECT = "android_support_bundle_collect"


def register_android_support_bundle_doctor(agent: Any) -> None:
    @agent.tool
    async def android_support_bundle_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_support_bundle_doctor_impl()


def register_android_support_bundle_plan(agent: Any) -> None:
    @agent.tool
    async def android_support_bundle_plan(
        context: RunContext,
        artifact_name: str = "droidpuppy_support_bundle",
    ) -> dict[str, Any]:
        del context
        return android_support_bundle_plan_impl(artifact_name=artifact_name)


def register_android_support_bundle_collect(agent: Any) -> None:
    @agent.tool
    async def android_support_bundle_collect(
        context: RunContext,
        artifact_name: str = "droidpuppy_support_bundle",
        dry_run: bool = True,
        include_screenshot: bool = True,
        include_logcat: bool = True,
        include_dumpsys: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_support_bundle_collect_impl(
            artifact_name=artifact_name,
            dry_run=dry_run,
            include_screenshot=include_screenshot,
            include_logcat=include_logcat,
            include_dumpsys=include_dumpsys,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_support_bundle_doctor},
        {"name": _PLAN, "register_func": register_android_support_bundle_plan},
        {"name": _COLLECT, "register_func": register_android_support_bundle_collect},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _PLAN, _COLLECT]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
