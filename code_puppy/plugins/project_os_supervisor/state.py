from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from .manifest_schema import (
    AUTHORITY_DAEMON_BUILTIN,
    DEFAULT_HOST_RUNTIME,
    DEFAULT_LOG_BACKUPS,
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_MANIFEST_VERSION,
    DEFAULT_MAX_RESTART_ATTEMPTS,
    DEFAULT_OPERATOR_MAX_EVENTS,
    DEFAULT_OPERATOR_TAIL_SECONDS,
    DEFAULT_RESTART_BACKOFF_SECONDS,
    AuthorityConfig,
    ManifestDocument,
    OperatorWorkflow,
    SandboxConfig,
    ServiceManifest,
    TemplateConfig,
    ToolHints,
    manifest_document_from_payload,
)

DEFAULT_SUPERVISOR_ROOT = Path.home() / ".project_os" / "supervisor"
EVENT_BUS_BUILTIN = "event_bus"

__all__ = [
    "AUTHORITY_DAEMON_BUILTIN",
    "DEFAULT_HOST_RUNTIME",
    "DEFAULT_LOG_BACKUPS",
    "DEFAULT_LOG_MAX_BYTES",
    "DEFAULT_MANIFEST_VERSION",
    "DEFAULT_MAX_RESTART_ATTEMPTS",
    "DEFAULT_OPERATOR_MAX_EVENTS",
    "DEFAULT_OPERATOR_TAIL_SECONDS",
    "DEFAULT_RESTART_BACKOFF_SECONDS",
    "AuthorityConfig",
    "ManifestDocument",
    "OperatorWorkflow",
    "SandboxConfig",
    "ServiceManifest",
    "TemplateConfig",
    "ToolHints",
    "clear_supervisor_state",
    "event_socket_path",
    "find_service",
    "get_supervisor_root",
    "heartbeat_path",
    "heartbeat_snapshot",
    "load_manifest",
    "load_manifest_document",
    "load_runtime",
    "log_path",
    "pid_alive",
    "read_json",
    "runtime_dir",
    "runtime_path",
    "runtime_payload",
    "runtime_status",
    "stop_path",
    "utc_now",
    "write_authority_manifest",
    "write_json",
    "write_runtime",
    "_rotate_log",
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def get_supervisor_root() -> Path:
    raw = os.environ.get("PROJECT_OS_SUPERVISOR_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_SUPERVISOR_ROOT


def _state_dir(name: str) -> Path:
    path = get_supervisor_root() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir() -> Path:
    return _state_dir("runtime")


def logs_dir() -> Path:
    return _state_dir("logs")


def heartbeats_dir() -> Path:
    return _state_dir("heartbeats")


def control_dir() -> Path:
    return _state_dir("control")


def bus_dir() -> Path:
    return _state_dir("bus")


def event_socket_path() -> Path:
    explicit = os.environ.get("PROJECT_OS_EVENT_SOCKET_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    digest = hashlib.sha1(str(get_supervisor_root()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"po-bus-{digest}.sock"


def _safe_name(value: str) -> str:
    cleaned = [char if char.isalnum() else "-" for char in value.strip().lower()]
    return "".join(cleaned).strip("-") or "service"


def _manifest_id(manifest_path: Path) -> str:
    return _safe_name(manifest_path.resolve().stem)


def _service_id(manifest_path: Path, service_name: str) -> str:
    return f"{_manifest_id(manifest_path)}__{_safe_name(service_name)}"


def runtime_path(manifest_path: Path, service_name: str) -> Path:
    return runtime_dir() / f"{_service_id(manifest_path, service_name)}.json"


def heartbeat_path(manifest_path: Path, service_name: str) -> Path:
    return heartbeats_dir() / f"{_service_id(manifest_path, service_name)}.json"


def log_path(manifest_path: Path, service_name: str) -> Path:
    return logs_dir() / f"{_service_id(manifest_path, service_name)}.log"


def stop_path(manifest_path: Path, service_name: str) -> Path:
    return control_dir() / f"{_service_id(manifest_path, service_name)}.stop"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _rotate_log(path: Path, *, max_bytes: int, backups: int) -> dict[str, Any]:
    if not path.exists():
        return {"rotated": False, "path": str(path)}
    size = path.stat().st_size
    if size < max_bytes:
        return {"rotated": False, "path": str(path), "size": size}
    for index in range(backups, 0, -1):
        src = path.with_name(f"{path.name}.{index}")
        dst = path.with_name(f"{path.name}.{index + 1}")
        if src.exists():
            if index == backups:
                src.unlink()
            else:
                src.replace(dst)
    path.replace(path.with_name(f"{path.name}.1"))
    return {"rotated": True, "path": str(path), "size": size}


def load_manifest_document(manifest_path: str | Path) -> ManifestDocument:
    path = Path(manifest_path).expanduser().resolve()
    return manifest_document_from_payload(read_json(path))


def load_manifest(manifest_path: str | Path) -> list[ServiceManifest]:
    return load_manifest_document(manifest_path).services


def write_authority_manifest(output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path).expanduser().resolve()
    document = ManifestDocument(
        manifest_version=DEFAULT_MANIFEST_VERSION,
        template=TemplateConfig(flavor="authority_stack.v1", strict_validation=False),
        authority=AuthorityConfig(
            principal_id="",
            required=False,
            enforce_handshake=False,
        ),
        operator_workflow=OperatorWorkflow(
            primary_service="authority-daemon",
            recommended_tail_topics=["system.authority", "authority.audit"],
            recommended_tail_seconds=DEFAULT_OPERATOR_TAIL_SECONDS,
            recommended_max_events=DEFAULT_OPERATOR_MAX_EVENTS,
            tool_hints=ToolHints(
                start="project_os_supervisor_start_manifest",
                snapshot="project_os_supervisor_operator_snapshot",
            ),
        ),
        services=[
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
            ),
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
            ),
        ],
    )
    payload = document.as_dict()
    write_json(path, payload)
    return {"success": True, "manifest_path": str(path), "manifest": payload}


def find_service(manifest_path: str | Path, service_name: str) -> ServiceManifest:
    for service in load_manifest(manifest_path):
        if service.name == service_name:
            return service
    raise ValueError(f"service '{service_name}' not found in manifest")


def runtime_payload(
    manifest_path: Path,
    service: ServiceManifest,
    **updates: Any,
) -> dict[str, Any]:
    payload = {
        "service_id": _service_id(manifest_path, service.name),
        "service_name": service.name,
        "manifest_path": str(manifest_path),
        "requested_command": service.command,
        "command": service.command,
        "requested_cwd": str(Path(service.cwd).expanduser())
        if service.runtime != "proot"
        else service.cwd,
        "cwd": str(Path(service.cwd).expanduser())
        if service.runtime != "proot"
        else service.cwd,
        "restart_policy": service.restart_policy,
        "runtime": service.runtime,
        "sandbox_name": service.sandbox_name,
        "sandbox_rootfs_tarball": service.sandbox_rootfs_tarball,
        "sandbox_rootfs_url": service.sandbox_rootfs_url,
        "sandbox_bind_mounts": service.sandbox_bind_mounts,
        "max_restart_attempts": service.max_restart_attempts,
        "heartbeat_timeout_seconds": service.heartbeat_timeout_seconds,
        "heartbeat_interval_seconds": service.heartbeat_interval_seconds,
        "log_path": str(log_path(manifest_path, service.name)),
        "heartbeat_path": str(heartbeat_path(manifest_path, service.name)),
        "monitor_pid": None,
        "child_pid": None,
        "state": "pending",
        "desired_state": "running",
        "restart_count": 0,
        "last_exit_code": None,
        "last_exit_at": None,
        "last_heartbeat_at": None,
        "last_heartbeat_age_seconds": None,
        "last_heartbeat_payload": None,
        "last_event": "created",
        "started_at": None,
        "updated_at": utc_now(),
    }
    payload.update(updates)
    payload["updated_at"] = utc_now()
    return payload


def load_runtime(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def write_runtime(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    updated["updated_at"] = utc_now()
    write_json(path, updated)
    return updated


def heartbeat_snapshot(
    path: Path,
) -> tuple[str | None, float | None, dict[str, Any] | None]:
    if not path.exists():
        return None, None, None
    try:
        payload = read_json(path)
    except Exception:
        return None, None, None
    ts = str(payload.get("heartbeat_at", "")) or None
    timestamp = float(payload.get("heartbeat_unix", 0) or 0)
    age = round(max(0.0, time.time() - timestamp), 3) if timestamp else None
    return ts, age, payload


def runtime_status(payload: dict[str, Any]) -> dict[str, Any]:
    heartbeat_age = payload.get("last_heartbeat_age_seconds")
    heartbeat_timeout = float(payload.get("heartbeat_timeout_seconds", 0) or 0)
    child_pid = int(payload.get("child_pid", 0) or 0) or None
    monitor_pid = int(payload.get("monitor_pid", 0) or 0) or None
    monitor_alive = pid_alive(monitor_pid)
    child_alive = pid_alive(child_pid)
    state = str(payload.get("state", "unknown"))
    health = "ok"
    if (
        heartbeat_timeout > 0
        and isinstance(heartbeat_age, (int, float))
        and heartbeat_age > heartbeat_timeout
    ):
        state = "heartbeat_stale"
        health = "degraded"
    elif state == "running" and not child_alive:
        state = "exited"
        health = "degraded"
    elif state == "running" and not monitor_alive:
        health = "degraded"
    elif state in {"crashed", "heartbeat_stale"}:
        health = "degraded"
    elif state in {"stopped", "exited"}:
        health = "stopped"
    summary = dict(payload)
    summary["state"] = state
    summary["health"] = health
    summary["monitor_alive"] = monitor_alive
    summary["child_alive"] = child_alive
    return summary


def clear_supervisor_state() -> dict[str, Any]:
    root = get_supervisor_root()
    if root.exists():
        shutil.rmtree(root)
    return {"success": True, "supervisor_root": str(root), "cleared": True}
