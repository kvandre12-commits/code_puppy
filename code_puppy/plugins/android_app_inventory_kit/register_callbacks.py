"""Register Android app inventory and profiling tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_app_inventory_doctor as android_app_inventory_doctor_impl,
    android_app_inventory_list as android_app_inventory_list_impl,
    android_app_profile as android_app_profile_impl,
)

_DOCTOR = "android_app_inventory_doctor"
_LIST = "android_app_inventory_list"
_PROFILE = "android_app_profile"



def register_android_app_inventory_doctor(agent: Any) -> None:
    @agent.tool
    async def android_app_inventory_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_app_inventory_doctor_impl()



def register_android_app_inventory_list(agent: Any) -> None:
    @agent.tool
    async def android_app_inventory_list(
        context: RunContext,
        query: str = "",
        max_results: int = 100,
        third_party_only: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_app_inventory_list_impl(
            query=query,
            max_results=max_results,
            third_party_only=third_party_only,
        )



def register_android_app_profile(agent: Any) -> None:
    @agent.tool
    async def android_app_profile(
        context: RunContext,
        package_name: str,
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_app_profile_impl(package_name=package_name, user=user)



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_app_inventory_doctor},
        {"name": _LIST, "register_func": register_android_app_inventory_list},
        {"name": _PROFILE, "register_func": register_android_app_profile},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _LIST, _PROFILE]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
