"""Register Android UI dump kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_ui_dump_doctor as android_ui_dump_doctor_impl,
    android_ui_dump_find as android_ui_dump_find_impl,
    android_ui_dump_hierarchy as android_ui_dump_hierarchy_impl,
)

_DOCTOR = "android_ui_dump_doctor"
_HIERARCHY = "android_ui_dump_hierarchy"
_FIND = "android_ui_dump_find"



def register_android_ui_dump_doctor(agent: Any) -> None:
    @agent.tool
    async def android_ui_dump_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_ui_dump_doctor_impl()



def register_android_ui_dump_hierarchy(agent: Any) -> None:
    @agent.tool
    async def android_ui_dump_hierarchy(
        context: RunContext,
        max_nodes: int = 200,
        include_xml: bool = False,
        max_xml_chars: int = 20000,
    ) -> dict[str, Any]:
        del context
        return android_ui_dump_hierarchy_impl(
            max_nodes=max_nodes,
            include_xml=include_xml,
            max_xml_chars=max_xml_chars,
        )



def register_android_ui_dump_find(agent: Any) -> None:
    @agent.tool
    async def android_ui_dump_find(
        context: RunContext,
        query: str = "",
        resource_id: str = "",
        class_name: str = "",
        clickable_only: bool = False,
        max_results: int = 50,
    ) -> dict[str, Any]:
        del context
        return android_ui_dump_find_impl(
            query=query,
            resource_id=resource_id,
            class_name=class_name,
            clickable_only=clickable_only,
            max_results=max_results,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_ui_dump_doctor},
        {"name": _HIERARCHY, "register_func": register_android_ui_dump_hierarchy},
        {"name": _FIND, "register_func": register_android_ui_dump_find},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _HIERARCHY, _FIND]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
