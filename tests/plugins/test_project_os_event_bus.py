from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from code_puppy.plugins.authority_gateway import audit
from code_puppy.plugins.project_os_supervisor import bus, tooling
from code_puppy.plugins.project_os_supervisor.state import event_socket_path


def _write_manifest(tmp_path: Path, services: list[dict]) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0.0", "services": services}, indent=2) + "\n"
    )
    return manifest_path


def _wait_for(predicate, timeout: float = 5.0, sleep: float = 0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(sleep)
    raise AssertionError("timed out waiting for condition")


def _event_bus_service() -> dict:
    return {
        "name": "event-bus",
        "builtin": "event_bus",
        "autostart": True,
        "restart_policy": "always",
        "restart_backoff_seconds": 0.1,
        "max_restart_attempts": 1,
        "heartbeat_timeout_seconds": 0.0,
        "log_max_bytes": 4096,
        "log_backups": 2,
    }


class TestProjectOsEventBus:
    def test_project_os_tail_receives_direct_system_publish(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        manifest_path = _write_manifest(tmp_path, [_event_bus_service()])
        tooling.project_os_supervisor_start_manifest(str(manifest_path))
        _wait_for(lambda: event_socket_path().exists())

        publisher = threading.Thread(
            target=lambda: (
                time.sleep(0.2),
                bus.publish_project_os_event_best_effort(
                    "system.test",
                    "smoke",
                    source="test_suite",
                    payload={"summary": "hello from bus"},
                ),
            )
        )
        publisher.start()
        result = tooling.project_os_tail(
            topics=["system.test"],
            seconds=2.0,
            max_events=1,
        )
        publisher.join(timeout=2)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["events"][0]["topic"] == "system.test"
        assert result["events"][0]["event_type"] == "smoke"
        assert "hello from bus" in result["lines"][0]

        tooling.project_os_supervisor_stop_manifest(str(manifest_path))

    def test_project_os_tail_receives_live_authority_audit_event(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path / "eyes"))
        manifest_path = _write_manifest(tmp_path, [_event_bus_service()])
        tooling.project_os_supervisor_start_manifest(str(manifest_path))
        _wait_for(lambda: event_socket_path().exists())

        publisher = threading.Thread(
            target=lambda: (
                time.sleep(0.2),
                audit.emit_authority_event(
                    "tool_blocked",
                    principal_id="principal-alpha",
                    tool_name="android_intent_send",
                    outcome="blocked",
                    reason="policy says no",
                    details={"block_kind": "policy"},
                ),
            )
        )
        publisher.start()
        result = tooling.project_os_tail(
            topics=["authority.audit"],
            seconds=2.0,
            max_events=1,
        )
        publisher.join(timeout=2)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["events"][0]["topic"] == "authority.audit"
        assert result["events"][0]["payload"]["event_type"] == "tool_blocked"
        assert "tool_blocked" in result["lines"][0]

        tooling.project_os_supervisor_stop_manifest(str(manifest_path))

    def test_authority_manifest_emits_live_authority_heartbeat(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path / "eyes"))
        manifest_result = tooling.project_os_supervisor_write_authority_manifest(
            output_path=str(tmp_path / "authority_manifest.json")
        )
        manifest_path = manifest_result["manifest_path"]

        start = tooling.project_os_supervisor_start_manifest(manifest_path)
        assert start["success"] is True
        _wait_for(lambda: event_socket_path().exists())

        result = tooling.project_os_tail(
            topics=["system.authority"],
            seconds=3.0,
            max_events=1,
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["events"][0]["topic"] == "system.authority"
        assert result["events"][0]["event_type"] == "authority_heartbeat"
        assert result["events"][0]["payload"]["service_name"] == "authority-daemon"

        tooling.project_os_supervisor_stop_manifest(manifest_path)
