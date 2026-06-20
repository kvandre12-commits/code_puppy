from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .bus import publish_project_os_event_best_effort
from .daemon import run_authority_daemon
from .state import (
    AUTHORITY_DAEMON_BUILTIN,
    DEFAULT_LOG_BACKUPS,
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_MAX_RESTART_ATTEMPTS,
    DEFAULT_RESTART_BACKOFF_SECONDS,
    ServiceManifest,
    clear_supervisor_state,
    find_service,
    get_supervisor_root,
    heartbeat_path,
    heartbeat_snapshot,
    load_manifest,
    load_runtime,
    log_path,
    pid_alive,
    runtime_dir,
    runtime_path,
    runtime_payload,
    runtime_status,
    stop_path,
    utc_now,
    write_authority_manifest,
    write_json,
    write_runtime,
    _rotate_log,
)

__all__ = [
    "DEFAULT_POLL_SECONDS",
    "DEFAULT_LOG_BACKUPS",
    "DEFAULT_LOG_MAX_BYTES",
    "DEFAULT_MAX_RESTART_ATTEMPTS",
    "DEFAULT_RESTART_BACKOFF_SECONDS",
    "AUTHORITY_DAEMON_BUILTIN",
    "ServiceManifest",
    "clear_supervisor_state",
    "get_supervisor_root",
    "load_manifest",
    "run_authority_daemon",
    "run_monitor",
    "start_manifest",
    "stop_manifest",
    "stop_service",
    "supervisor_status",
    "write_authority_manifest",
    "_rotate_log",
]

DEFAULT_POLL_SECONDS = 0.5


def _publish_service_event(
    event_type: str,
    *,
    manifest_path: Path,
    service: ServiceManifest,
    payload: dict[str, Any] | None = None,
) -> None:
    publish_project_os_event_best_effort(
        "system.service",
        event_type,
        source="project_os_supervisor",
        payload={
            "service_name": service.name,
            "manifest_path": str(manifest_path),
            **(payload or {}),
        },
    )


def _terminate_tree(child: subprocess.Popen[Any] | None) -> int | None:
    if child is None:
        return None
    if child.poll() is not None:
        return child.returncode
    child.terminate()
    try:
        return child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        try:
            return child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            return None


def _should_restart(service: ServiceManifest, exit_code: int | None) -> bool:
    if service.restart_policy == "never":
        return False
    if service.restart_policy == "always":
        return True
    return bool(exit_code)


def _start_child(
    manifest_path: Path, service: ServiceManifest
) -> subprocess.Popen[Any]:
    hb_path = heartbeat_path(manifest_path, service.name)
    lg_path = log_path(manifest_path, service.name)
    _rotate_log(lg_path, max_bytes=service.log_max_bytes, backups=service.log_backups)
    environment = os.environ.copy()
    environment.update(service.env)
    environment.update(
        {
            "PROJECT_OS_SERVICE_NAME": service.name,
            "PROJECT_OS_HEARTBEAT_PATH": str(hb_path),
            "PROJECT_OS_SUPERVISOR_ROOT": str(get_supervisor_root()),
            "PROJECT_OS_SUPERVISOR_MANIFEST": str(manifest_path),
            "PROJECT_OS_HEARTBEAT_INTERVAL_SECONDS": str(
                service.heartbeat_interval_seconds
            ),
        }
    )
    cwd = Path(service.cwd).expanduser().resolve()
    handle = lg_path.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            service.command,
            cwd=str(cwd),
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    finally:
        handle.close()
    return process


def run_monitor(manifest_path: str | Path, service_name: str) -> int:
    manifest = Path(manifest_path).expanduser().resolve()
    service = find_service(manifest, service_name)
    rt_path = runtime_path(manifest, service.name)
    hb_path = heartbeat_path(manifest, service.name)
    st_path = stop_path(manifest, service.name)
    restart_count = 0
    child: subprocess.Popen[Any] | None = None

    try:
        while True:
            if st_path.exists():
                st_path.unlink(missing_ok=True)
                exit_code = _terminate_tree(child)
                write_runtime(
                    rt_path,
                    runtime_payload(
                        manifest,
                        service,
                        monitor_pid=os.getpid(),
                        child_pid=None,
                        state="stopped",
                        desired_state="stopped",
                        restart_count=restart_count,
                        last_exit_code=exit_code,
                        last_exit_at=utc_now(),
                        last_event="stopped_by_operator",
                    ),
                )
                _publish_service_event(
                    "service_stopped",
                    manifest_path=manifest,
                    service=service,
                    payload={
                        "exit_code": exit_code,
                        "restart_count": restart_count,
                    },
                )
                return 0

            child = _start_child(manifest, service)
            runtime = runtime_payload(
                manifest,
                service,
                monitor_pid=os.getpid(),
                child_pid=child.pid,
                state="running",
                desired_state="running",
                restart_count=restart_count,
                started_at=utc_now(),
                last_event="child_started",
            )
            write_runtime(rt_path, runtime)
            _publish_service_event(
                "service_started",
                manifest_path=manifest,
                service=service,
                payload={"child_pid": child.pid, "restart_count": restart_count},
            )

            stale = False
            while True:
                if st_path.exists():
                    break
                heartbeat_at, heartbeat_age, heartbeat_payload = heartbeat_snapshot(
                    hb_path
                )
                current = load_runtime(rt_path) or runtime
                current.update(
                    {
                        "monitor_pid": os.getpid(),
                        "child_pid": child.pid if child.poll() is None else None,
                        "last_heartbeat_at": heartbeat_at,
                        "last_heartbeat_age_seconds": heartbeat_age,
                        "last_heartbeat_payload": heartbeat_payload,
                        "state": "running"
                        if child.poll() is None
                        else current.get("state", "running"),
                        "desired_state": "running",
                        "restart_count": restart_count,
                        "last_event": "heartbeat_observed"
                        if heartbeat_at
                        else current.get("last_event", "child_started"),
                    }
                )
                write_runtime(rt_path, current)

                if (
                    service.heartbeat_timeout_seconds > 0
                    and heartbeat_age is not None
                    and heartbeat_age > service.heartbeat_timeout_seconds
                ):
                    stale = True
                    _terminate_tree(child)
                    break
                if child.poll() is not None:
                    break
                time.sleep(DEFAULT_POLL_SECONDS)

            if st_path.exists():
                continue

            exit_code = (
                child.wait(timeout=5) if child.poll() is None else child.returncode
            )
            event = "heartbeat_stale" if stale else "child_exited"
            should_restart = _should_restart(service, exit_code)
            if stale and service.restart_policy != "never":
                should_restart = True

            if should_restart and restart_count < service.max_restart_attempts:
                restart_count += 1
                write_runtime(
                    rt_path,
                    runtime_payload(
                        manifest,
                        service,
                        monitor_pid=os.getpid(),
                        child_pid=None,
                        state="restarting",
                        desired_state="running",
                        restart_count=restart_count,
                        last_exit_code=exit_code,
                        last_exit_at=utc_now(),
                        last_event=event,
                    ),
                )
                _publish_service_event(
                    "service_restarting",
                    manifest_path=manifest,
                    service=service,
                    payload={
                        "exit_code": exit_code,
                        "restart_count": restart_count,
                        "reason": event,
                    },
                )
                time.sleep(service.restart_backoff_seconds)
                continue

            final_state = "crashed" if exit_code else "exited"
            if stale:
                final_state = "heartbeat_stale"
            write_runtime(
                rt_path,
                runtime_payload(
                    manifest,
                    service,
                    monitor_pid=os.getpid(),
                    child_pid=None,
                    state=final_state,
                    desired_state="running",
                    restart_count=restart_count,
                    last_exit_code=exit_code,
                    last_exit_at=utc_now(),
                    last_event=event,
                ),
            )
            _publish_service_event(
                f"service_{final_state}",
                manifest_path=manifest,
                service=service,
                payload={
                    "exit_code": exit_code,
                    "restart_count": restart_count,
                    "reason": event,
                },
            )
            return int(exit_code or 0)
    finally:
        if child and child.poll() is None:
            _terminate_tree(child)


def _spawn_monitor(manifest_path: Path, service_name: str) -> dict[str, Any]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "code_puppy.plugins.project_os_supervisor",
            "run-monitor",
            "--manifest",
            str(manifest_path),
            "--service",
            service_name,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
        env={**os.environ, "PROJECT_OS_SUPERVISOR_ROOT": str(get_supervisor_root())},
    )
    return {"service_name": service_name, "monitor_pid": process.pid, "started": True}


def list_statuses(
    manifest_path: str | Path | None = None,
    service_name: str = "",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    filter_manifest = (
        str(Path(manifest_path).expanduser().resolve()) if manifest_path else None
    )
    for path in sorted(runtime_dir().glob("*.json")):
        payload = load_runtime(path)
        if not payload:
            continue
        if filter_manifest and payload.get("manifest_path") != filter_manifest:
            continue
        if service_name and payload.get("service_name") != service_name:
            continue
        results.append(runtime_status(payload))
    return results


def supervisor_status(
    manifest_path: str | Path | None = None,
    service_name: str = "",
) -> dict[str, Any]:
    statuses = list_statuses(manifest_path=manifest_path, service_name=service_name)
    return {
        "success": True,
        "supervisor_root": str(get_supervisor_root()),
        "count": len(statuses),
        "services": statuses,
        "summary": {
            "running": sum(1 for item in statuses if item["state"] == "running"),
            "restarting": sum(1 for item in statuses if item["state"] == "restarting"),
            "stopped": sum(1 for item in statuses if item["health"] == "stopped"),
            "degraded": sum(1 for item in statuses if item["health"] == "degraded"),
        },
    }


def start_manifest(manifest_path: str | Path, service_name: str = "") -> dict[str, Any]:
    manifest = Path(manifest_path).expanduser().resolve()
    services = load_manifest(manifest)
    started: list[dict[str, Any]] = []
    for service in services:
        if service_name and service.name != service_name:
            continue
        if not service.autostart and not service_name:
            continue
        current = load_runtime(runtime_path(manifest, service.name))
        if current and pid_alive(int(current.get("monitor_pid", 0) or 0)):
            started.append(
                {
                    "service_name": service.name,
                    "monitor_pid": current.get("monitor_pid"),
                    "started": False,
                    "reason": "already_running",
                }
            )
            continue
        started.append(_spawn_monitor(manifest, service.name))
    return {"success": True, "manifest_path": str(manifest), "started": started}


def stop_service(manifest_path: str | Path, service_name: str) -> dict[str, Any]:
    manifest = Path(manifest_path).expanduser().resolve()
    rt_path = runtime_path(manifest, service_name)
    runtime = load_runtime(rt_path)
    write_json(stop_path(manifest, service_name), {"requested_at": utc_now()})
    if runtime:
        payload = dict(runtime)
        payload["desired_state"] = "stopped"
        payload["last_event"] = "stop_requested"
        write_runtime(rt_path, payload)
    return {
        "success": True,
        "manifest_path": str(manifest),
        "service_name": service_name,
        "stop_requested": True,
    }


def stop_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest = Path(manifest_path).expanduser().resolve()
    stopped = [
        stop_service(manifest, service.name)
        for service in load_manifest(manifest)
        if load_runtime(runtime_path(manifest, service.name)) is not None
    ]
    return {
        "success": True,
        "manifest_path": str(manifest),
        "count": len(stopped),
        "services": stopped,
    }
