from __future__ import annotations

from typing import Any

from .manager import (
    clear_supervisor_state,
    start_manifest,
    stop_manifest,
    stop_service,
    supervisor_status,
    write_authority_manifest,
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
