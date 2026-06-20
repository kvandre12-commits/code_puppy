from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    project_os_supervisor_init_sandbox as project_os_supervisor_init_sandbox_impl,
    project_os_supervisor_reset_state as project_os_supervisor_reset_state_impl,
    project_os_supervisor_start_manifest as project_os_supervisor_start_manifest_impl,
    project_os_supervisor_status as project_os_supervisor_status_impl,
    project_os_supervisor_stop_manifest as project_os_supervisor_stop_manifest_impl,
    project_os_supervisor_stop_service as project_os_supervisor_stop_service_impl,
    project_os_supervisor_write_authority_manifest as project_os_supervisor_write_authority_manifest_impl,
    project_os_tail as project_os_tail_impl,
)

_STATUS = "project_os_supervisor_status"
_WRITE_MANIFEST = "project_os_supervisor_write_authority_manifest"
_INIT_SANDBOX = "project_os_supervisor_init_sandbox"
_START_MANIFEST = "project_os_supervisor_start_manifest"
_STOP_SERVICE = "project_os_supervisor_stop_service"
_STOP_MANIFEST = "project_os_supervisor_stop_manifest"
_RESET_STATE = "project_os_supervisor_reset_state"
_TAIL = "project_os_tail"


def register_project_os_supervisor_status(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_status(
        context: RunContext,
        manifest_path: str = "",
        service_name: str = "",
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_status_impl(
            manifest_path=manifest_path,
            service_name=service_name,
        )


def register_project_os_supervisor_write_authority_manifest(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_write_authority_manifest(
        context: RunContext,
        output_path: str = "outputs/project_os_authority_manifest.json",
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_write_authority_manifest_impl(
            output_path=output_path,
        )


def register_project_os_supervisor_init_sandbox(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_init_sandbox(
        context: RunContext,
        manifest_path: str = "",
        service_name: str = "",
        sandbox_name: str = "default",
        rootfs_tarball: str = "",
        rootfs_url: str = "",
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_init_sandbox_impl(
            manifest_path=manifest_path,
            service_name=service_name,
            sandbox_name=sandbox_name,
            rootfs_tarball=rootfs_tarball,
            rootfs_url=rootfs_url,
        )


def register_project_os_supervisor_start_manifest(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_start_manifest(
        context: RunContext,
        manifest_path: str,
        service_name: str = "",
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_start_manifest_impl(
            manifest_path=manifest_path,
            service_name=service_name,
        )


def register_project_os_supervisor_stop_service(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_stop_service(
        context: RunContext,
        manifest_path: str,
        service_name: str,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_stop_service_impl(
            manifest_path=manifest_path,
            service_name=service_name,
        )


def register_project_os_supervisor_stop_manifest(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_stop_manifest(
        context: RunContext,
        manifest_path: str,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_stop_manifest_impl(manifest_path=manifest_path)


def register_project_os_supervisor_reset_state(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_reset_state(
        context: RunContext,
        confirm: bool = False,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_reset_state_impl(confirm=confirm)


def register_project_os_tail(agent: Any) -> None:
    @agent.tool
    async def project_os_tail(
        context: RunContext,
        topics: list[str] | None = None,
        seconds: float = 3.0,
        max_events: int = 20,
    ) -> dict[str, Any]:
        del context
        return project_os_tail_impl(
            topics=topics,
            seconds=seconds,
            max_events=max_events,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _STATUS, "register_func": register_project_os_supervisor_status},
        {
            "name": _WRITE_MANIFEST,
            "register_func": register_project_os_supervisor_write_authority_manifest,
        },
        {
            "name": _INIT_SANDBOX,
            "register_func": register_project_os_supervisor_init_sandbox,
        },
        {
            "name": _START_MANIFEST,
            "register_func": register_project_os_supervisor_start_manifest,
        },
        {
            "name": _STOP_SERVICE,
            "register_func": register_project_os_supervisor_stop_service,
        },
        {
            "name": _STOP_MANIFEST,
            "register_func": register_project_os_supervisor_stop_manifest,
        },
        {
            "name": _RESET_STATE,
            "register_func": register_project_os_supervisor_reset_state,
        },
        {"name": _TAIL, "register_func": register_project_os_tail},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _STATUS,
        _WRITE_MANIFEST,
        _INIT_SANDBOX,
        _START_MANIFEST,
        _STOP_SERVICE,
        _STOP_MANIFEST,
        _RESET_STATE,
        _TAIL,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
