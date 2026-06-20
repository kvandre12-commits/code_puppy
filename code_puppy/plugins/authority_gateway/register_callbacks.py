from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .policy import build_pre_tool_response, handle_post_tool_result
from .tooling import (
    authority_gateway_list_active_leases as authority_gateway_list_active_leases_impl,
    authority_gateway_quarantine_status as authority_gateway_quarantine_status_impl,
    authority_gateway_recent_audit as authority_gateway_recent_audit_impl,
    authority_gateway_release_quarantine as authority_gateway_release_quarantine_impl,
    authority_gateway_revoke_all as authority_gateway_revoke_all_impl,
    authority_gateway_status as authority_gateway_status_impl,
)

_STATUS = "authority_gateway_status"
_LIST_ACTIVE_LEASES = "authority_gateway_list_active_leases"
_RECENT_AUDIT = "authority_gateway_recent_audit"
_QUARANTINE_STATUS = "authority_gateway_quarantine_status"
_RELEASE_QUARANTINE = "authority_gateway_release_quarantine"
_REVOKE_ALL = "authority_gateway_revoke_all"


async def on_pre_tool_call(
    tool_name: str, tool_args: dict[str, Any], context: Any = None
) -> dict[str, Any] | None:
    del context
    return build_pre_tool_response(tool_name, tool_args)


async def on_post_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    result: Any,
    duration_ms: float,
    context: Any = None,
) -> None:
    del tool_args, duration_ms, context
    handle_post_tool_result(tool_name, result)


def register_authority_gateway_status(agent: Any) -> None:
    @agent.tool
    async def authority_gateway_status(context: RunContext) -> dict[str, Any]:
        del context
        return authority_gateway_status_impl()


def register_authority_gateway_list_active_leases(agent: Any) -> None:
    @agent.tool
    async def authority_gateway_list_active_leases(
        context: RunContext,
        principal_id: str = "",
    ) -> dict[str, Any]:
        del context
        return authority_gateway_list_active_leases_impl(principal_id=principal_id)


def register_authority_gateway_recent_audit(agent: Any) -> None:
    @agent.tool
    async def authority_gateway_recent_audit(
        context: RunContext,
        limit: int = 20,
        principal_id: str = "",
    ) -> dict[str, Any]:
        del context
        return authority_gateway_recent_audit_impl(
            limit=limit,
            principal_id=principal_id,
        )


def register_authority_gateway_quarantine_status(agent: Any) -> None:
    @agent.tool
    async def authority_gateway_quarantine_status(
        context: RunContext,
        principal_id: str = "",
    ) -> dict[str, Any]:
        del context
        return authority_gateway_quarantine_status_impl(principal_id=principal_id)


def register_authority_gateway_release_quarantine(agent: Any) -> None:
    @agent.tool
    async def authority_gateway_release_quarantine(
        context: RunContext,
        principal_id: str,
        reason: str = "Manual operator quarantine release.",
        released_by: str = "operator",
    ) -> dict[str, Any]:
        del context
        return authority_gateway_release_quarantine_impl(
            principal_id=principal_id,
            reason=reason,
            released_by=released_by,
        )


def register_authority_gateway_revoke_all(agent: Any) -> None:
    @agent.tool
    async def authority_gateway_revoke_all(
        context: RunContext,
        principal_id: str = "",
        reason: str = "Manual operator revoke-all override.",
        revoked_by: str = "operator",
    ) -> dict[str, Any]:
        del context
        return authority_gateway_revoke_all_impl(
            principal_id=principal_id,
            reason=reason,
            revoked_by=revoked_by,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _STATUS, "register_func": register_authority_gateway_status},
        {
            "name": _LIST_ACTIVE_LEASES,
            "register_func": register_authority_gateway_list_active_leases,
        },
        {
            "name": _RECENT_AUDIT,
            "register_func": register_authority_gateway_recent_audit,
        },
        {
            "name": _QUARANTINE_STATUS,
            "register_func": register_authority_gateway_quarantine_status,
        },
        {
            "name": _RELEASE_QUARANTINE,
            "register_func": register_authority_gateway_release_quarantine,
        },
        {"name": _REVOKE_ALL, "register_func": register_authority_gateway_revoke_all},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _STATUS,
        _LIST_ACTIVE_LEASES,
        _RECENT_AUDIT,
        _QUARANTINE_STATUS,
        _RELEASE_QUARANTINE,
        _REVOKE_ALL,
    ]


register_callback("pre_tool_call", on_pre_tool_call)
register_callback("post_tool_call", on_post_tool_call)
register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
