from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SUPERVISOR_ROOT = Path.home() / ".project_os" / "supervisor"
DEFAULT_LOG_MAX_BYTES = 128 * 1024
DEFAULT_LOG_BACKUPS = 3
DEFAULT_RESTART_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_RESTART_ATTEMPTS = 3
AUTHORITY_DAEMON_BUILTIN = "authority_daemon"
EVENT_BUS_BUILTIN = "event_bus"
DEFAULT_SANDBOX_NAME = "default"


@dataclass(frozen=True)
class ServiceManifest:
    name: str
    command: list[str]
    cwd: str
    env: dict[str, str]
    autostart: bool
    restart_policy: str
    restart_backoff_seconds: float
    max_restart_attempts: int
    heartbeat_timeout_seconds: float
    heartbeat_interval_seconds: float
    log_max_bytes: int
    log_backups: int
    builtin: str
    runtime: str
    sandbox_name: str
    sandbox_rootfs_tarball: str
    sandbox_rootfs_url: str
    sandbox_bind_mounts: list[str]

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
            "heartbeat_timeout_seconds": self.heartbeat_timeout_seconds,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "log_max_bytes": self.log_max_bytes,
            "log_backups": self.log_backups,
            "builtin": self.builtin,
            "runtime": self.runtime,
            "sandbox_name": self.sandbox_name,
            "sandbox_rootfs_tarball": self.sandbox_rootfs_tarball,
            "sandbox_rootfs_url": self.sandbox_rootfs_url,
            "sandbox_bind_mounts": self.sandbox_bind_mounts,
        }


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


def _normalize_command(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item).strip()]


def _normalize_string_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _service_from_payload(payload: dict[str, Any]) -> ServiceManifest:
    name = str(payload.get("name", "")).strip()
    builtin = str(payload.get("builtin", "")).strip()
    runtime = str(payload.get("runtime", "direct") or "direct").strip().lower()
    command = _normalize_command(payload.get("command"))
    if runtime not in {"direct", "proot"}:
        raise ValueError(f"service '{name or 'unknown'}' has invalid runtime")
    if builtin == AUTHORITY_DAEMON_BUILTIN and not command:
        if runtime == "proot":
            raise ValueError(
                f"service '{name or 'unknown'}' must define an explicit guest command when runtime=proot"
            )
        command = [
            sys.executable,
            "-m",
            "code_puppy.plugins.project_os_supervisor",
            "run-authority-daemon",
        ]
    if builtin == EVENT_BUS_BUILTIN and not command:
        if runtime == "proot":
            raise ValueError(
                f"service '{name or 'unknown'}' must define an explicit guest command when runtime=proot"
            )
        command = [
            sys.executable,
            "-m",
            "code_puppy.plugins.project_os_supervisor",
            "run-broker",
        ]
    if not name:
        raise ValueError("service name is required")
    if not command:
        raise ValueError(f"service '{name}' must define command or builtin")
    restart_policy = str(payload.get("restart_policy", "on-failure")).strip() or "never"
    if restart_policy not in {"never", "on-failure", "always"}:
        raise ValueError(f"service '{name}' has invalid restart_policy")
    env = payload.get("env") if isinstance(payload.get("env"), dict) else {}
    return ServiceManifest(
        name=name,
        command=command,
        cwd=str(payload.get("cwd", ".") or "."),
        env={str(key): str(value) for key, value in env.items()},
        autostart=bool(payload.get("autostart", True)),
        restart_policy=restart_policy,
        restart_backoff_seconds=float(
            payload.get("restart_backoff_seconds", DEFAULT_RESTART_BACKOFF_SECONDS)
        ),
        max_restart_attempts=max(
            0,
            int(payload.get("max_restart_attempts", DEFAULT_MAX_RESTART_ATTEMPTS) or 0),
        ),
        heartbeat_timeout_seconds=max(
            0.0, float(payload.get("heartbeat_timeout_seconds", 0) or 0)
        ),
        heartbeat_interval_seconds=max(
            0.1, float(payload.get("heartbeat_interval_seconds", 5) or 5)
        ),
        log_max_bytes=max(
            1024, int(payload.get("log_max_bytes", DEFAULT_LOG_MAX_BYTES) or 0)
        ),
        log_backups=max(1, int(payload.get("log_backups", DEFAULT_LOG_BACKUPS) or 0)),
        builtin=builtin,
        runtime=runtime,
        sandbox_name=str(
            payload.get("sandbox_name", DEFAULT_SANDBOX_NAME) or DEFAULT_SANDBOX_NAME
        ).strip()
        or DEFAULT_SANDBOX_NAME,
        sandbox_rootfs_tarball=str(
            payload.get("sandbox_rootfs_tarball", "") or ""
        ).strip(),
        sandbox_rootfs_url=str(payload.get("sandbox_rootfs_url", "") or "").strip(),
        sandbox_bind_mounts=_normalize_string_list(payload.get("sandbox_bind_mounts")),
    )


def load_manifest(manifest_path: str | Path) -> list[ServiceManifest]:
    path = Path(manifest_path).expanduser().resolve()
    payload = read_json(path)
    services = (
        payload.get("services") if isinstance(payload.get("services"), list) else []
    )
    records = [_service_from_payload(service) for service in services]
    names = [service.name for service in records]
    if len(names) != len(set(names)):
        raise ValueError("manifest contains duplicate service names")
    return records


def write_authority_manifest(output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path).expanduser().resolve()
    payload = {
        "manifest_version": "1.0.0",
        "services": [
            {
                "name": "event-bus",
                "builtin": EVENT_BUS_BUILTIN,
                "autostart": True,
                "restart_policy": "always",
                "restart_backoff_seconds": 1.0,
                "max_restart_attempts": 5,
                "heartbeat_timeout_seconds": 0.0,
                "log_max_bytes": DEFAULT_LOG_MAX_BYTES,
                "log_backups": DEFAULT_LOG_BACKUPS,
            },
            {
                "name": "authority-daemon",
                "builtin": AUTHORITY_DAEMON_BUILTIN,
                "autostart": True,
                "restart_policy": "always",
                "restart_backoff_seconds": 1.0,
                "max_restart_attempts": 5,
                "heartbeat_interval_seconds": 2.0,
                "heartbeat_timeout_seconds": 8.0,
                "log_max_bytes": DEFAULT_LOG_MAX_BYTES,
                "log_backups": DEFAULT_LOG_BACKUPS,
            },
        ],
    }
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
