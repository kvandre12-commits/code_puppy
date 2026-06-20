from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from code_puppy.plugins.project_os_supervisor import __main__ as main_mod
from code_puppy.plugins.project_os_supervisor import (
    manager,
    register_callbacks,
    tooling,
)


def _write_manifest(tmp_path: Path, services: list[dict]) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0.0", "services": services}, indent=2) + "\n"
    )
    return manifest_path


def _wait_for(predicate, timeout: float = 5.0, sleep: float = 0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(sleep)
    raise AssertionError("timed out waiting for condition")


class TestProjectOsSupervisorRegistration:
    def test_register_tools_callback_exposes_surface(self):
        specs = register_callbacks.register_tools_callback()
        names = {spec["name"] for spec in specs}
        assert names == {
            "project_os_supervisor_status",
            "project_os_supervisor_write_authority_manifest",
            "project_os_supervisor_init_sandbox",
            "project_os_supervisor_start_manifest",
            "project_os_supervisor_stop_service",
            "project_os_supervisor_stop_manifest",
            "project_os_supervisor_reset_state",
            "project_os_tail",
        }

    def test_register_agent_tools_advertises_same_surface(self):
        assert register_callbacks._advertise_tools_to_agent("code-puppy") == [
            "project_os_supervisor_status",
            "project_os_supervisor_write_authority_manifest",
            "project_os_supervisor_init_sandbox",
            "project_os_supervisor_start_manifest",
            "project_os_supervisor_stop_service",
            "project_os_supervisor_stop_manifest",
            "project_os_supervisor_reset_state",
            "project_os_tail",
        ]


class TestProjectOsSupervisorTooling:
    def test_write_authority_manifest_helper(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        result = tooling.project_os_supervisor_write_authority_manifest(
            output_path=str(tmp_path / "authority.json")
        )

        assert result["success"] is True
        manifest = json.loads(Path(result["manifest_path"]).read_text())
        assert [service["builtin"] for service in manifest["services"]] == [
            "event_bus",
            "authority_daemon",
        ]

    def test_authority_daemon_start_status_and_stop(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        manifest_path = _write_manifest(
            tmp_path,
            [
                {
                    "name": "authority-daemon",
                    "builtin": "authority_daemon",
                    "autostart": True,
                    "restart_policy": "always",
                    "restart_backoff_seconds": 0.1,
                    "max_restart_attempts": 2,
                    "heartbeat_interval_seconds": 0.2,
                    "heartbeat_timeout_seconds": 2.0,
                    "log_max_bytes": 4096,
                    "log_backups": 2,
                }
            ],
        )

        start = tooling.project_os_supervisor_start_manifest(str(manifest_path))
        assert start["success"] is True
        assert start["started"][0]["started"] is True

        running = _wait_for(
            lambda: next(
                (
                    service
                    for service in tooling.project_os_supervisor_status(
                        manifest_path=str(manifest_path)
                    )["services"]
                    if service["service_name"] == "authority-daemon"
                    and service["state"] == "running"
                    and service.get("last_heartbeat_payload")
                ),
                None,
            )
        )
        assert running["child_alive"] is True
        assert running["monitor_alive"] is True
        assert running["last_heartbeat_payload"]["beat"] >= 1

        stop = tooling.project_os_supervisor_stop_service(
            manifest_path=str(manifest_path),
            service_name="authority-daemon",
        )
        assert stop["success"] is True

        stopped = _wait_for(
            lambda: next(
                (
                    service
                    for service in tooling.project_os_supervisor_status(
                        manifest_path=str(manifest_path)
                    )["services"]
                    if service["service_name"] == "authority-daemon"
                    and "stopped" in service["state"]
                ),
                None,
            )
        )
        assert stopped["desired_state"] == "stopped"

    def test_on_failure_restart_policy_restarts_then_marks_crashed(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        manifest_path = _write_manifest(
            tmp_path,
            [
                {
                    "name": "boom",
                    "command": [sys.executable, "-c", "import sys; sys.exit(7)"],
                    "cwd": str(tmp_path),
                    "autostart": True,
                    "restart_policy": "on-failure",
                    "restart_backoff_seconds": 0.1,
                    "max_restart_attempts": 2,
                    "heartbeat_timeout_seconds": 0,
                    "log_max_bytes": 2048,
                    "log_backups": 2,
                }
            ],
        )

        result = tooling.project_os_supervisor_start_manifest(str(manifest_path))
        assert result["success"] is True

        crashed = _wait_for(
            lambda: next(
                (
                    service
                    for service in tooling.project_os_supervisor_status(
                        manifest_path=str(manifest_path)
                    )["services"]
                    if service["service_name"] == "boom"
                    and service["state"] == "crashed"
                ),
                None,
            ),
            timeout=8,
        )
        assert crashed["last_exit_code"] == 7
        assert crashed["restart_count"] == 2

    def test_rotate_log_keeps_backups(self, tmp_path):
        log_path = tmp_path / "service.log"
        backup = tmp_path / "service.log.1"
        log_path.write_text("x" * 20)
        backup.write_text("older")

        result = manager._rotate_log(log_path, max_bytes=10, backups=2)

        assert result["rotated"] is True
        assert not log_path.exists()
        assert (tmp_path / "service.log.1").read_text() == "x" * 20
        assert (tmp_path / "service.log.2").read_text() == "older"

    def test_cli_status_prints_json(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        manifest_path = _write_manifest(
            tmp_path,
            [
                {
                    "name": "authority-daemon",
                    "builtin": "authority_daemon",
                    "autostart": True,
                    "restart_policy": "always",
                    "restart_backoff_seconds": 0.1,
                    "max_restart_attempts": 1,
                    "heartbeat_interval_seconds": 0.2,
                    "heartbeat_timeout_seconds": 2.0,
                }
            ],
        )
        tooling.project_os_supervisor_start_manifest(str(manifest_path))
        _wait_for(
            lambda: any(
                service["state"] == "running"
                for service in tooling.project_os_supervisor_status(
                    manifest_path=str(manifest_path)
                )["services"]
            )
        )

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "project-os-supervisor",
                "status",
                "--manifest",
                str(manifest_path),
            ],
        )
        try:
            main_mod.main()
        except SystemExit as exc:
            assert exc.code == 0

        output = json.loads(capsys.readouterr().out)
        assert output["success"] is True
        assert output["count"] == 1
        assert output["services"][0]["service_name"] == "authority-daemon"

        tooling.project_os_supervisor_stop_manifest(str(manifest_path))
