from __future__ import annotations

from typing import Any

from .bus import get_project_os_bus_status, tail_project_os_events
from .inspection import inspect_manifest
from .manager import (
    clear_supervisor_state,
    initialize_sandbox,
    start_manifest,
    stop_manifest,
    stop_service,
    supervisor_status,
    write_authority_manifest,
)
from .templates import (
    operator_snapshot,
    start_isolated_job,
    write_isolated_job_manifest,
)


def project_os_supervisor_status(
    manifest_path: str = "",
    service_name: str = "",
) -> dict[str, Any]:
    return supervisor_status(
        manifest_path=manifest_path or None,
        service_name=service_name,
    )


def project_os_supervisor_write_authority_manifest(
    output_path: str = "outputs/project_os_authority_manifest.json",
) -> dict[str, Any]:
    return write_authority_manifest(output_path)


def project_os_supervisor_inspect_manifest(
    manifest_path: str,
) -> dict[str, Any]:
    if not manifest_path.strip():
        return {
            "manifest_path": "",
            "valid": False,
            "version": "",
            "template_flavor": "",
            "primary_service": "",
            "runtime_summary": {},
            "warnings": [],
            "errors": ["manifest_path is required"],
        }
    return inspect_manifest(manifest_path)


def project_os_supervisor_init_sandbox(
    manifest_path: str = "",
    service_name: str = "",
    sandbox_name: str = "default",
    rootfs_tarball: str = "",
    rootfs_url: str = "",
) -> dict[str, Any]:
    return initialize_sandbox(
        manifest_path=manifest_path or None,
        service_name=service_name,
        sandbox_name=sandbox_name,
        rootfs_tarball=rootfs_tarball,
        rootfs_url=rootfs_url,
    )


def project_os_supervisor_start_manifest(
    manifest_path: str,
    service_name: str = "",
) -> dict[str, Any]:
    if not manifest_path.strip():
        return {"success": False, "reason": "manifest_path is required"}
    return start_manifest(manifest_path=manifest_path, service_name=service_name)


def project_os_supervisor_stop_service(
    manifest_path: str,
    service_name: str,
) -> dict[str, Any]:
    if not manifest_path.strip() or not service_name.strip():
        return {
            "success": False,
            "reason": "manifest_path and service_name are required",
        }
    return stop_service(manifest_path=manifest_path, service_name=service_name)


def project_os_supervisor_stop_manifest(manifest_path: str) -> dict[str, Any]:
    if not manifest_path.strip():
        return {"success": False, "reason": "manifest_path is required"}
    return stop_manifest(manifest_path=manifest_path)


def project_os_supervisor_reset_state(confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {
            "success": False,
            "reason": "Set confirm=True to clear supervisor state.",
        }
    return clear_supervisor_state()


def project_os_supervisor_write_isolated_job_manifest(
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
    return write_isolated_job_manifest(
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


def project_os_supervisor_start_isolated_job(
    manifest_path: str,
    service_name: str = "",
    tail_topics: list[str] | None = None,
    tail_seconds: float = 0.5,
    tail_max_events: int = 10,
) -> dict[str, Any]:
    if not manifest_path.strip():
        return {"success": False, "reason": "manifest_path is required"}
    return start_isolated_job(
        manifest_path=manifest_path,
        service_name=service_name,
        tail_topics=tail_topics,
        tail_seconds=tail_seconds,
        tail_max_events=tail_max_events,
    )


def project_os_supervisor_operator_snapshot(
    manifest_path: str,
    service_name: str = "",
    topics: list[str] | None = None,
    seconds: float = 0.5,
    max_events: int = 10,
) -> dict[str, Any]:
    if not manifest_path.strip():
        return {"success": False, "reason": "manifest_path is required"}
    return operator_snapshot(
        manifest_path=manifest_path,
        service_name=service_name,
        topics=topics,
        seconds=seconds,
        max_events=max_events,
    )


def project_os_bus_status(timeout_seconds: float = 0.5) -> dict[str, Any]:
    return get_project_os_bus_status(timeout_seconds=timeout_seconds)


def project_os_tail(
    topics: list[str] | None = None,
    seconds: float = 3.0,
    max_events: int = 20,
) -> dict[str, Any]:
    return tail_project_os_events(
        topics=topics,
        seconds=seconds,
        max_events=max_events,
    )
