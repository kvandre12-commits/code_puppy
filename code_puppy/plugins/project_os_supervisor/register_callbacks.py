from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    project_os_supervisor_init_sandbox as project_os_supervisor_init_sandbox_impl,
    project_os_supervisor_inspect_manifest as project_os_supervisor_inspect_manifest_impl,
    project_os_supervisor_operator_snapshot as project_os_supervisor_operator_snapshot_impl,
    project_os_supervisor_reset_state as project_os_supervisor_reset_state_impl,
    project_os_supervisor_start_isolated_job as project_os_supervisor_start_isolated_job_impl,
    project_os_supervisor_start_manifest as project_os_supervisor_start_manifest_impl,
    project_os_supervisor_status as project_os_supervisor_status_impl,
    project_os_supervisor_stop_manifest as project_os_supervisor_stop_manifest_impl,
    project_os_supervisor_stop_service as project_os_supervisor_stop_service_impl,
    project_os_supervisor_write_authority_manifest as project_os_supervisor_write_authority_manifest_impl,
    project_os_supervisor_write_isolated_job_manifest as project_os_supervisor_write_isolated_job_manifest_impl,
    project_os_bus_status as project_os_bus_status_impl,
    project_os_tail as project_os_tail_impl,
)

_STATUS = "project_os_supervisor_status"
_WRITE_MANIFEST = "project_os_supervisor_write_authority_manifest"
_INSPECT_MANIFEST = "project_os_supervisor_inspect_manifest"
_INIT_SANDBOX = "project_os_supervisor_init_sandbox"
_START_MANIFEST = "project_os_supervisor_start_manifest"
_START_ISOLATED_JOB = "project_os_supervisor_start_isolated_job"
_STOP_SERVICE = "project_os_supervisor_stop_service"
_STOP_MANIFEST = "project_os_supervisor_stop_manifest"
_RESET_STATE = "project_os_supervisor_reset_state"
_WRITE_ISOLATED_JOB_MANIFEST = "project_os_supervisor_write_isolated_job_manifest"
_OPERATOR_SNAPSHOT = "project_os_supervisor_operator_snapshot"
_BUS_STATUS = "project_os_bus_status"
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


def register_project_os_supervisor_inspect_manifest(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_inspect_manifest(
        context: RunContext,
        manifest_path: str,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_inspect_manifest_impl(
            manifest_path=manifest_path,
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


def register_project_os_supervisor_start_isolated_job(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_start_isolated_job(
        context: RunContext,
        manifest_path: str,
        service_name: str = "",
        tail_topics: list[str] | None = None,
        tail_seconds: float = 0.5,
        tail_max_events: int = 10,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_start_isolated_job_impl(
            manifest_path=manifest_path,
            service_name=service_name,
            tail_topics=tail_topics,
            tail_seconds=tail_seconds,
            tail_max_events=tail_max_events,
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


def register_project_os_supervisor_write_isolated_job_manifest(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_write_isolated_job_manifest(
        context: RunContext,
        output_path: str = "outputs/project_os_isolated_job_manifest.json",
        service_name: str = "isolated-job",
        command: list[str] | None = None,
        runtime: str = "proot",
        sandbox_name: str = "isolated-job",
        sandbox_rootfs_tarball: str = "",
        sandbox_rootfs_url: str = "",
        sandbox_bind_mounts: list[str] | None = None,
        cwd: str = "",
        env: dict[str, str] | None = None,
        principal_id: str = "",
        include_authority: bool = True,
        autostart: bool = False,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_write_isolated_job_manifest_impl(
            output_path=output_path,
            service_name=service_name,
            command=command,
            runtime=runtime,
            sandbox_name=sandbox_name,
            sandbox_rootfs_tarball=sandbox_rootfs_tarball,
            sandbox_rootfs_url=sandbox_rootfs_url,
            sandbox_bind_mounts=sandbox_bind_mounts,
            cwd=cwd,
            env=env,
            principal_id=principal_id,
            include_authority=include_authority,
            autostart=autostart,
        )


def register_project_os_supervisor_operator_snapshot(agent: Any) -> None:
    @agent.tool
    async def project_os_supervisor_operator_snapshot(
        context: RunContext,
        manifest_path: str,
        service_name: str = "",
        topics: list[str] | None = None,
        seconds: float = 0.5,
        max_events: int = 10,
    ) -> dict[str, Any]:
        del context
        return project_os_supervisor_operator_snapshot_impl(
            manifest_path=manifest_path,
            service_name=service_name,
            topics=topics,
            seconds=seconds,
            max_events=max_events,
        )


def register_project_os_bus_status(agent: Any) -> None:
    @agent.tool
    async def project_os_bus_status(
        context: RunContext,
        timeout_seconds: float = 0.5,
    ) -> dict[str, Any]:
        del context
        return project_os_bus_status_impl(timeout_seconds=timeout_seconds)


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
            "name": _INSPECT_MANIFEST,
            "register_func": register_project_os_supervisor_inspect_manifest,
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
            "name": _START_ISOLATED_JOB,
            "register_func": register_project_os_supervisor_start_isolated_job,
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
        {
            "name": _WRITE_ISOLATED_JOB_MANIFEST,
            "register_func": register_project_os_supervisor_write_isolated_job_manifest,
        },
        {
            "name": _OPERATOR_SNAPSHOT,
            "register_func": register_project_os_supervisor_operator_snapshot,
        },
        {"name": _BUS_STATUS, "register_func": register_project_os_bus_status},
        {"name": _TAIL, "register_func": register_project_os_tail},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _STATUS,
        _WRITE_MANIFEST,
        _INSPECT_MANIFEST,
        _INIT_SANDBOX,
        _START_MANIFEST,
        _START_ISOLATED_JOB,
        _STOP_SERVICE,
        _STOP_MANIFEST,
        _RESET_STATE,
        _WRITE_ISOLATED_JOB_MANIFEST,
        _OPERATOR_SNAPSHOT,
        _BUS_STATUS,
        _TAIL,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
