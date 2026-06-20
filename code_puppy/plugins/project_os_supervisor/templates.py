from __future__ import annotations

from pathlib import Path
from typing import Any

from code_puppy.plugins.authority_gateway.lease_store import get_default_principal_id

from .bus import tail_project_os_events
from .manager import initialize_sandbox, start_manifest, supervisor_status
from .state import (
    AUTHORITY_DAEMON_BUILTIN,
    DEFAULT_HOST_RUNTIME,
    DEFAULT_LOG_BACKUPS,
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_MANIFEST_VERSION,
    DEFAULT_MAX_RESTART_ATTEMPTS,
    DEFAULT_RESTART_BACKOFF_SECONDS,
    EVENT_BUS_BUILTIN,
    AuthorityConfig,
    ManifestDocument,
    OperatorWorkflow,
    SandboxConfig,
    ServiceManifest,
    TemplateConfig,
    ToolHints,
    find_service,
    load_manifest,
    load_manifest_document,
    manifest_document_from_payload,
    write_json,
)

DEFAULT_OPERATOR_TAIL_TOPICS = [
    "system.service",
    "system.authority",
    "authority.audit",
]
DEFAULT_OPERATOR_TAIL_SECONDS = 0.5
DEFAULT_OPERATOR_MAX_EVENTS = 10
DEFAULT_PROOT_WORKSPACE = "/workspace"
_DEFAULT_TEMPLATE_VERSION = "isolated_job.v1"


def _authority_service_specs() -> list[dict[str, Any]]:
    return [
        ServiceManifest(
            name="event-bus",
            cwd=".",
            builtin=EVENT_BUS_BUILTIN,
            autostart=True,
            restart_policy="always",
            restart_backoff_seconds=1.0,
            max_restart_attempts=5,
            heartbeat_timeout_seconds=0.0,
            heartbeat_interval_seconds=5.0,
            log_max_bytes=DEFAULT_LOG_MAX_BYTES,
            log_backups=DEFAULT_LOG_BACKUPS,
        ).as_dict(),
        ServiceManifest(
            name="authority-daemon",
            cwd=".",
            builtin=AUTHORITY_DAEMON_BUILTIN,
            autostart=True,
            restart_policy="always",
            restart_backoff_seconds=1.0,
            max_restart_attempts=5,
            heartbeat_interval_seconds=2.0,
            heartbeat_timeout_seconds=8.0,
            log_max_bytes=DEFAULT_LOG_MAX_BYTES,
            log_backups=DEFAULT_LOG_BACKUPS,
        ).as_dict(),
    ]


def _normalize_command(command: list[str] | None) -> list[str]:
    if not isinstance(command, list):
        return []
    return [str(item).strip() for item in command if str(item).strip()]


def _normalize_env(env: dict[str, str] | None) -> dict[str, str]:
    if not isinstance(env, dict):
        return {}
    return {
        str(key).strip(): str(value) for key, value in env.items() if str(key).strip()
    }


def _normalize_bind_mounts(bind_mounts: list[str] | None) -> list[str]:
    if not isinstance(bind_mounts, list):
        return []
    return [str(item).strip() for item in bind_mounts if str(item).strip()]


def _normalize_runtime(runtime: str) -> str:
    clean_runtime = runtime.strip().lower() or "proot"
    if clean_runtime == "direct":
        return DEFAULT_HOST_RUNTIME
    return clean_runtime


def _job_services(manifest_path: str | Path) -> list[str]:
    services = load_manifest(manifest_path)
    return [
        service.name
        for service in services
        if service.builtin not in {AUTHORITY_DAEMON_BUILTIN, EVENT_BUS_BUILTIN}
    ]


def _manifest_has_authority(manifest_path: str | Path) -> bool:
    document = load_manifest_document(manifest_path)
    if document.authority.required:
        return True
    builtins = {service.builtin for service in document.services if service.builtin}
    return AUTHORITY_DAEMON_BUILTIN in builtins or EVENT_BUS_BUILTIN in builtins


def _resolve_primary_service(
    manifest_path: str | Path,
    service_name: str = "",
) -> str:
    requested = service_name.strip()
    if requested:
        find_service(manifest_path, requested)
        return requested

    document = load_manifest_document(manifest_path)
    primary = document.operator_workflow.primary_service.strip()
    if primary:
        find_service(manifest_path, primary)
        return primary

    jobs = _job_services(manifest_path)
    if len(jobs) == 1:
        return jobs[0]
    if not jobs:
        raise ValueError("manifest does not define a non-builtin job service")
    raise ValueError(
        "manifest defines multiple non-builtin job services; pass service_name explicitly"
    )


def _workflow_payload(
    *,
    service_name: str,
    tail_topics: list[str] | None = None,
) -> dict[str, Any]:
    topics = tail_topics or DEFAULT_OPERATOR_TAIL_TOPICS
    return {
        "primary_service": service_name,
        "recommended_tail_topics": topics,
        "recommended_tail_seconds": DEFAULT_OPERATOR_TAIL_SECONDS,
        "recommended_max_events": DEFAULT_OPERATOR_MAX_EVENTS,
        "tool_hints": {
            "start": "project_os_supervisor_start_isolated_job",
            "snapshot": "project_os_supervisor_operator_snapshot",
        },
    }


def write_isolated_job_manifest(
    output_path: str | Path,
    *,
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
    restart_policy: str = "never",
    restart_backoff_seconds: float = DEFAULT_RESTART_BACKOFF_SECONDS,
    max_restart_attempts: int = DEFAULT_MAX_RESTART_ATTEMPTS,
    heartbeat_interval_seconds: float = 5.0,
    heartbeat_timeout_seconds: float = 0.0,
) -> dict[str, Any]:
    path = Path(output_path).expanduser().resolve()
    clean_name = service_name.strip()
    clean_runtime = _normalize_runtime(runtime)
    clean_command = _normalize_command(command)
    if not clean_name:
        return {"success": False, "reason": "service_name is required"}
    if clean_runtime not in {DEFAULT_HOST_RUNTIME, "proot"}:
        return {
            "success": False,
            "reason": "runtime must be one of: host, direct, proot",
        }
    if not clean_command:
        return {"success": False, "reason": "command must contain at least one token"}

    default_cwd = DEFAULT_PROOT_WORKSPACE if clean_runtime == "proot" else "."
    job_env = {
        "PROJECT_OS_PRINCIPAL_ID": principal_id.strip() or get_default_principal_id(),
        "PYTHONUNBUFFERED": "1",
        **_normalize_env(env),
    }
    bind_mounts = _normalize_bind_mounts(sandbox_bind_mounts)
    if clean_runtime == "proot" and not bind_mounts:
        bind_mounts = [f".:{DEFAULT_PROOT_WORKSPACE}"]

    sandbox = None
    if clean_runtime == "proot":
        sandbox = SandboxConfig(
            name=sandbox_name.strip() or clean_name,
            rootfs_tarball=sandbox_rootfs_tarball.strip(),
            rootfs_url=sandbox_rootfs_url.strip(),
            bind_mounts=bind_mounts,
        )

    services = [*_authority_service_specs()] if include_authority else []
    services.append(
        ServiceManifest(
            name=clean_name,
            command=clean_command,
            cwd=cwd.strip() or default_cwd,
            env=job_env,
            autostart=autostart,
            restart_policy=restart_policy,
            restart_backoff_seconds=max(0.0, float(restart_backoff_seconds)),
            max_restart_attempts=max(0, int(max_restart_attempts)),
            heartbeat_interval_seconds=max(0.1, float(heartbeat_interval_seconds)),
            heartbeat_timeout_seconds=max(0.0, float(heartbeat_timeout_seconds)),
            log_max_bytes=DEFAULT_LOG_MAX_BYTES,
            log_backups=DEFAULT_LOG_BACKUPS,
            runtime=clean_runtime,
            sandbox=sandbox,
        ).as_dict()
    )
    document = ManifestDocument(
        manifest_version=DEFAULT_MANIFEST_VERSION,
        template=TemplateConfig(
            flavor=_DEFAULT_TEMPLATE_VERSION,
            strict_validation=True,
        ),
        authority=AuthorityConfig(
            principal_id=job_env["PROJECT_OS_PRINCIPAL_ID"],
            required=include_authority,
            enforce_handshake=include_authority,
        ),
        operator_workflow=OperatorWorkflow(
            primary_service=clean_name,
            recommended_tail_topics=DEFAULT_OPERATOR_TAIL_TOPICS,
            recommended_tail_seconds=DEFAULT_OPERATOR_TAIL_SECONDS,
            recommended_max_events=DEFAULT_OPERATOR_MAX_EVENTS,
            tool_hints=ToolHints(
                start="project_os_supervisor_start_isolated_job",
                snapshot="project_os_supervisor_operator_snapshot",
            ),
        ),
        services=manifest_document_from_payload({"services": services}).services,
    )
    payload = document.as_dict()
    write_json(path, payload)
    return {
        "success": True,
        "manifest_path": str(path),
        "manifest": payload,
        "workflow": payload["operator_workflow"],
    }


def start_isolated_job(
    manifest_path: str | Path,
    *,
    service_name: str = "",
    tail_topics: list[str] | None = None,
    tail_seconds: float = DEFAULT_OPERATOR_TAIL_SECONDS,
    tail_max_events: int = DEFAULT_OPERATOR_MAX_EVENTS,
) -> dict[str, Any]:
    try:
        manifest = Path(manifest_path).expanduser().resolve()
        primary_service = _resolve_primary_service(manifest, service_name)
        service = find_service(manifest, primary_service)
        workflow = operator_snapshot(
            manifest,
            service_name=primary_service,
            topics=tail_topics,
            seconds=0.01,
            max_events=0,
        )["workflow"]

        if service.runtime == "proot":
            sandbox_result = initialize_sandbox(
                manifest_path=manifest,
                service_name=primary_service,
            )
            if not sandbox_result.get("success"):
                return {
                    "success": False,
                    "manifest_path": str(manifest),
                    "primary_service": primary_service,
                    "sandbox": sandbox_result,
                    "reason": sandbox_result.get("reason", "sandbox init failed"),
                }
        else:
            sandbox_result = {
                "success": True,
                "skipped": True,
                "reason": "service runtime is not proot",
            }

        authority_start = start_manifest(manifest)
        job_start = start_manifest(manifest, service_name=primary_service)
        status = supervisor_status(manifest_path=manifest)
        topics = tail_topics or workflow["recommended_tail_topics"]
        success = bool(authority_start.get("success") and job_start.get("success"))
        return {
            "success": success,
            "manifest_path": str(manifest),
            "primary_service": primary_service,
            "sandbox": sandbox_result,
            "authority_start": authority_start,
            "job_start": job_start,
            "status": status,
            "workflow": workflow,
            "tail_hint": {
                "tool_name": "project_os_tail",
                "topics": topics,
                "seconds": max(0.0, float(tail_seconds)),
                "max_events": max(0, int(tail_max_events)),
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "manifest_path": str(Path(manifest_path).expanduser().resolve()),
            "reason": str(exc),
        }


def operator_snapshot(
    manifest_path: str | Path,
    *,
    service_name: str = "",
    topics: list[str] | None = None,
    seconds: float = DEFAULT_OPERATOR_TAIL_SECONDS,
    max_events: int = DEFAULT_OPERATOR_MAX_EVENTS,
) -> dict[str, Any]:
    try:
        manifest = Path(manifest_path).expanduser().resolve()
        primary_service = _resolve_primary_service(manifest, service_name)
        document = load_manifest_document(manifest)
        workflow_payload = {
            **_workflow_payload(
                service_name=primary_service,
                tail_topics=topics,
            ),
            **document.operator_workflow.as_dict(),
            "primary_service": primary_service,
            "recommended_tail_topics": topics
            or document.operator_workflow.recommended_tail_topics
            or DEFAULT_OPERATOR_TAIL_TOPICS,
        }
        status = supervisor_status(manifest_path=manifest)
        tail = tail_project_os_events(
            topics=workflow_payload["recommended_tail_topics"],
            seconds=max(0.0, float(seconds)),
            max_events=max(0, int(max_events)),
        )
        return {
            "success": bool(status.get("success") and tail.get("success")),
            "manifest_path": str(manifest),
            "primary_service": primary_service,
            "workflow": workflow_payload,
            "status": status,
            "tail": tail,
            "summary": (
                f"primary_service={primary_service}; "
                f"running={status['summary']['running']}; "
                f"degraded={status['summary']['degraded']}; "
                f"tail_events={tail['count']}"
            ),
        }
    except Exception as exc:
        return {
            "success": False,
            "manifest_path": str(Path(manifest_path).expanduser().resolve()),
            "reason": str(exc),
        }
