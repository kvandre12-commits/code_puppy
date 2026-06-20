from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

DEFAULT_LOG_MAX_BYTES = 128 * 1024
DEFAULT_LOG_BACKUPS = 3
DEFAULT_RESTART_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_RESTART_ATTEMPTS = 3
DEFAULT_MANIFEST_VERSION = "1.0.0"
DEFAULT_TEMPLATE_FLAVOR = "generic.v1"
DEFAULT_OPERATOR_TAIL_SECONDS = 0.5
DEFAULT_OPERATOR_MAX_EVENTS = 10
DEFAULT_SERVICE_CWD = "/workspace"
DEFAULT_HOST_CWD = "."
DEFAULT_HOST_RUNTIME = "host"
LEGACY_HOST_RUNTIME = "direct"
AUTHORITY_DAEMON_BUILTIN = "authority_daemon"
EVENT_BUS_BUILTIN = "event_bus"
DEFAULT_SANDBOX_NAME = "default"


@dataclass(frozen=True)
class SandboxConfig:
    name: str
    rootfs_tarball: str = ""
    rootfs_url: str = ""
    bind_mounts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rootfs_tarball": self.rootfs_tarball,
            "rootfs_url": self.rootfs_url,
            "bind_mounts": self.bind_mounts,
        }


@dataclass(frozen=True)
class ServiceManifest:
    name: str
    command: list[str] = field(default_factory=list)
    cwd: str = DEFAULT_SERVICE_CWD
    env: dict[str, str] = field(default_factory=dict)
    autostart: bool = False
    restart_policy: str = "never"
    restart_backoff_seconds: float = DEFAULT_RESTART_BACKOFF_SECONDS
    max_restart_attempts: int = DEFAULT_MAX_RESTART_ATTEMPTS
    heartbeat_interval_seconds: float = 0.0
    heartbeat_timeout_seconds: float = 0.0
    log_max_bytes: int = DEFAULT_LOG_MAX_BYTES
    log_backups: int = DEFAULT_LOG_BACKUPS
    builtin: str | None = None
    runtime: str = DEFAULT_HOST_RUNTIME
    sandbox: SandboxConfig | None = None

    @property
    def sandbox_name(self) -> str:
        return self.sandbox.name if self.sandbox else DEFAULT_SANDBOX_NAME

    @property
    def sandbox_rootfs_tarball(self) -> str:
        return self.sandbox.rootfs_tarball if self.sandbox else ""

    @property
    def sandbox_rootfs_url(self) -> str:
        return self.sandbox.rootfs_url if self.sandbox else ""

    @property
    def sandbox_bind_mounts(self) -> list[str]:
        return list(self.sandbox.bind_mounts) if self.sandbox else []

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "cwd": self.cwd,
            "env": self.env,
            "autostart": self.autostart,
            "restart_policy": self.restart_policy,
            "restart_backoff_seconds": self.restart_backoff_seconds,
            "max_restart_attempts": self.max_restart_attempts,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "heartbeat_timeout_seconds": self.heartbeat_timeout_seconds,
            "log_max_bytes": self.log_max_bytes,
            "log_backups": self.log_backups,
            "builtin": self.builtin,
            "runtime": self.runtime,
            "sandbox": self.sandbox.as_dict() if self.sandbox else None,
        }


@dataclass(frozen=True)
class AuthorityConfig:
    principal_id: str
    required: bool = True
    enforce_handshake: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "required": self.required,
            "enforce_handshake": self.enforce_handshake,
        }


@dataclass(frozen=True)
class ToolHints:
    start: str
    snapshot: str

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start, "snapshot": self.snapshot}


@dataclass(frozen=True)
class OperatorWorkflow:
    primary_service: str
    recommended_tail_topics: list[str] = field(default_factory=list)
    recommended_tail_seconds: float = DEFAULT_OPERATOR_TAIL_SECONDS
    recommended_max_events: int = DEFAULT_OPERATOR_MAX_EVENTS
    tool_hints: ToolHints | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "primary_service": self.primary_service,
            "recommended_tail_topics": self.recommended_tail_topics,
            "recommended_tail_seconds": self.recommended_tail_seconds,
            "recommended_max_events": self.recommended_max_events,
            "tool_hints": self.tool_hints.as_dict() if self.tool_hints else None,
        }


@dataclass(frozen=True)
class TemplateConfig:
    flavor: str
    strict_validation: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "flavor": self.flavor,
            "strict_validation": self.strict_validation,
        }


@dataclass(frozen=True)
class ManifestDocument:
    manifest_version: str
    template: TemplateConfig
    authority: AuthorityConfig
    operator_workflow: OperatorWorkflow
    services: list[ServiceManifest]

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "template": self.template.as_dict(),
            "authority": self.authority.as_dict(),
            "operator_workflow": self.operator_workflow.as_dict(),
            "services": [service.as_dict() for service in self.services],
        }


def _normalize_command(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _normalize_string_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _normalize_string_dict(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {
        str(key).strip(): str(value) for key, value in raw.items() if str(key).strip()
    }


def normalize_runtime(raw: Any) -> str:
    runtime = str(raw or DEFAULT_HOST_RUNTIME).strip().lower()
    if runtime == LEGACY_HOST_RUNTIME:
        return DEFAULT_HOST_RUNTIME
    if runtime not in {DEFAULT_HOST_RUNTIME, "proot"}:
        raise ValueError(f"invalid runtime: {runtime}")
    return runtime


def _default_cwd_for_runtime(runtime: str) -> str:
    return DEFAULT_SERVICE_CWD if runtime == "proot" else DEFAULT_HOST_CWD


def _sandbox_from_payload(
    payload: dict[str, Any],
    *,
    runtime: str,
    service_name: str,
) -> SandboxConfig | None:
    nested = (
        payload.get("sandbox") if isinstance(payload.get("sandbox"), dict) else None
    )
    legacy_name = str(payload.get("sandbox_name", "") or "").strip()
    legacy_tarball = str(payload.get("sandbox_rootfs_tarball", "") or "").strip()
    legacy_url = str(payload.get("sandbox_rootfs_url", "") or "").strip()
    legacy_binds = _normalize_string_list(payload.get("sandbox_bind_mounts"))

    if nested is not None:
        name = str(nested.get("name", "") or legacy_name or service_name).strip()
        rootfs_tarball = str(nested.get("rootfs_tarball", "") or legacy_tarball).strip()
        rootfs_url = str(nested.get("rootfs_url", "") or legacy_url).strip()
        bind_mounts = _normalize_string_list(nested.get("bind_mounts")) or legacy_binds
    else:
        name = legacy_name
        rootfs_tarball = legacy_tarball
        rootfs_url = legacy_url
        bind_mounts = legacy_binds

    has_any_sandbox_config = any(
        [name.strip(), rootfs_tarball, rootfs_url, bind_mounts]
    )
    if runtime == "proot" and not has_any_sandbox_config:
        name = service_name
        has_any_sandbox_config = True
    if runtime != "proot" and not has_any_sandbox_config:
        return None

    if not name.strip():
        name = DEFAULT_SANDBOX_NAME

    return SandboxConfig(
        name=name.strip() or DEFAULT_SANDBOX_NAME,
        rootfs_tarball=rootfs_tarball,
        rootfs_url=rootfs_url,
        bind_mounts=bind_mounts,
    )


def _builtin_command(name: str, builtin: str | None, runtime: str) -> list[str]:
    if not builtin:
        return []
    if runtime == "proot":
        raise ValueError(
            f"service '{name or 'unknown'}' must define an explicit guest command when runtime=proot"
        )
    if builtin == AUTHORITY_DAEMON_BUILTIN:
        return [
            sys.executable,
            "-m",
            "code_puppy.plugins.project_os_supervisor",
            "run-authority-daemon",
        ]
    if builtin == EVENT_BUS_BUILTIN:
        return [
            sys.executable,
            "-m",
            "code_puppy.plugins.project_os_supervisor",
            "run-broker",
        ]
    return []


def service_from_payload(payload: dict[str, Any]) -> ServiceManifest:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("service name is required")

    builtin = str(payload.get("builtin", "") or "").strip() or None
    runtime = normalize_runtime(payload.get("runtime", DEFAULT_HOST_RUNTIME))
    command = _normalize_command(payload.get("command")) or _builtin_command(
        name, builtin, runtime
    )
    if not command:
        raise ValueError(f"service '{name}' must define command or builtin")

    restart_policy = str(payload.get("restart_policy", "on-failure")).strip() or "never"
    if restart_policy not in {"never", "on-failure", "always"}:
        raise ValueError(f"service '{name}' has invalid restart_policy")

    return ServiceManifest(
        name=name,
        command=command,
        cwd=str(payload.get("cwd", "") or _default_cwd_for_runtime(runtime)),
        env=_normalize_string_dict(payload.get("env")),
        autostart=bool(payload.get("autostart", True)),
        restart_policy=restart_policy,
        restart_backoff_seconds=float(
            payload.get("restart_backoff_seconds", DEFAULT_RESTART_BACKOFF_SECONDS)
        ),
        max_restart_attempts=max(
            0,
            int(payload.get("max_restart_attempts", DEFAULT_MAX_RESTART_ATTEMPTS) or 0),
        ),
        heartbeat_interval_seconds=max(
            0.1, float(payload.get("heartbeat_interval_seconds", 5) or 5)
        ),
        heartbeat_timeout_seconds=max(
            0.0, float(payload.get("heartbeat_timeout_seconds", 0) or 0)
        ),
        log_max_bytes=max(
            1024, int(payload.get("log_max_bytes", DEFAULT_LOG_MAX_BYTES) or 0)
        ),
        log_backups=max(1, int(payload.get("log_backups", DEFAULT_LOG_BACKUPS) or 0)),
        builtin=builtin,
        runtime=runtime,
        sandbox=_sandbox_from_payload(payload, runtime=runtime, service_name=name),
    )


def _template_from_payload(raw: Any) -> TemplateConfig:
    if isinstance(raw, str) and raw.strip():
        return TemplateConfig(flavor=raw.strip(), strict_validation=False)
    if isinstance(raw, dict):
        flavor = str(raw.get("flavor", "") or DEFAULT_TEMPLATE_FLAVOR).strip()
        return TemplateConfig(
            flavor=flavor or DEFAULT_TEMPLATE_FLAVOR,
            strict_validation=bool(raw.get("strict_validation", True)),
        )
    return TemplateConfig(flavor=DEFAULT_TEMPLATE_FLAVOR, strict_validation=False)


def _authority_from_payload(raw: Any) -> AuthorityConfig:
    if not isinstance(raw, dict):
        return AuthorityConfig(
            principal_id="",
            required=False,
            enforce_handshake=False,
        )
    return AuthorityConfig(
        principal_id=str(raw.get("principal_id", "") or "").strip(),
        required=bool(raw.get("required", True)),
        enforce_handshake=bool(raw.get("enforce_handshake", True)),
    )


def _tool_hints_from_payload(raw: Any) -> ToolHints | None:
    if isinstance(raw, dict):
        start = str(raw.get("start", "") or "").strip()
        snapshot = str(raw.get("snapshot", "") or "").strip()
    elif isinstance(raw, tuple) and len(raw) == 2:
        start, snapshot = raw
        start = str(start).strip()
        snapshot = str(snapshot).strip()
    else:
        return None
    if not start and not snapshot:
        return None
    return ToolHints(start=start, snapshot=snapshot)


def _default_primary_service(services: list[ServiceManifest]) -> str:
    jobs = [
        service.name
        for service in services
        if service.builtin not in {AUTHORITY_DAEMON_BUILTIN, EVENT_BUS_BUILTIN}
    ]
    if len(jobs) == 1:
        return jobs[0]
    return jobs[0] if jobs else ""


def _workflow_from_payload(
    raw: Any,
    *,
    services: list[ServiceManifest],
) -> OperatorWorkflow:
    payload = raw if isinstance(raw, dict) else {}
    tool_hints = _tool_hints_from_payload(payload.get("tool_hints"))
    if tool_hints is None:
        tool_hints = _tool_hints_from_payload(
            (payload.get("start_tool", ""), payload.get("snapshot_tool", ""))
        )
    return OperatorWorkflow(
        primary_service=str(
            payload.get("primary_service", "") or _default_primary_service(services)
        ).strip(),
        recommended_tail_topics=_normalize_string_list(
            payload.get("recommended_tail_topics")
        ),
        recommended_tail_seconds=max(
            0.0,
            float(
                payload.get("recommended_tail_seconds", DEFAULT_OPERATOR_TAIL_SECONDS)
                or DEFAULT_OPERATOR_TAIL_SECONDS
            ),
        ),
        recommended_max_events=max(
            0,
            int(
                payload.get("recommended_max_events", DEFAULT_OPERATOR_MAX_EVENTS)
                or DEFAULT_OPERATOR_MAX_EVENTS
            ),
        ),
        tool_hints=tool_hints,
    )


def validate_manifest_document(document: ManifestDocument) -> None:
    if not document.manifest_version.strip():
        raise ValueError("manifest_version is required")
    if not document.template.flavor.strip():
        raise ValueError("template.flavor is required")
    if not document.services:
        raise ValueError("services must contain at least one entry")

    names = [service.name for service in document.services]
    if len(names) != len(set(names)):
        raise ValueError("manifest contains duplicate service names")

    service_names = set(names)
    primary = document.operator_workflow.primary_service.strip()
    if primary and primary not in service_names:
        raise ValueError(
            f"operator_workflow.primary_service '{primary}' not found in services"
        )

    if document.template.strict_validation:
        if not primary:
            raise ValueError(
                "operator_workflow.primary_service is required when strict_validation=true"
            )
        if document.authority.required:
            builtins = {
                service.builtin for service in document.services if service.builtin
            }
            if (
                AUTHORITY_DAEMON_BUILTIN not in builtins
                or EVENT_BUS_BUILTIN not in builtins
            ):
                raise ValueError(
                    "authority.required=true requires both event_bus and authority_daemon services"
                )
            if not document.authority.principal_id.strip():
                raise ValueError(
                    "authority.principal_id is required when authority.required=true"
                )


def manifest_document_from_payload(payload: dict[str, Any]) -> ManifestDocument:
    services_payload = (
        payload.get("services") if isinstance(payload.get("services"), list) else []
    )
    services = [service_from_payload(service) for service in services_payload]
    document = ManifestDocument(
        manifest_version=str(
            payload.get("manifest_version", DEFAULT_MANIFEST_VERSION)
            or DEFAULT_MANIFEST_VERSION
        ).strip(),
        template=_template_from_payload(payload.get("template")),
        authority=_authority_from_payload(payload.get("authority")),
        operator_workflow=_workflow_from_payload(
            payload.get("operator_workflow"),
            services=services,
        ),
        services=services,
    )
    validate_manifest_document(document)
    return document
