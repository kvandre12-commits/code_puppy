from __future__ import annotations

import json
from pathlib import Path

from code_puppy.plugins.authority_gateway import anomaly, register_callbacks, tooling
from code_puppy.plugins.authority_gateway.lease_store import get_default_principal_id
from code_puppy.plugins.authority_gateway.policy import build_pre_tool_response


def _write_lease(tmp_path: Path, payload: dict) -> Path:
    leases_dir = tmp_path / "leases" / "active"
    leases_dir.mkdir(parents=True, exist_ok=True)
    lease_path = leases_dir / f"{payload['lease_id']}.json"
    lease_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return lease_path


def _v2_lease(
    lease_id: str,
    *,
    principal_id: str | None = None,
    capabilities: list[str] | None = None,
) -> dict:
    return {
        "contract_version": "2.0.0",
        "lease_id": lease_id,
        "review_id": f"review-{lease_id}",
        "result_id": f"result-{lease_id}",
        "artifact_id": f"artifact-{lease_id}",
        "worker_class": "manual_triage",
        "issued_by": "butcher",
        "principal_id": principal_id or get_default_principal_id(),
        "lease_scope": "custom_scope",
        "capabilities": capabilities or ["shell.exec"],
        "allowed_tools": [],
        "constraints": {},
        "quotas": {
            "max_uses": 2,
            "remaining_uses": 2,
            "max_tool_calls": 2,
            "max_shell_commands": 2,
            "max_token_spend": None,
            "tool_calls_used": 0,
            "shell_commands_used": 0,
            "token_spend_used": 0,
        },
        "status": "active",
        "decision_event_ref": f"audit-{lease_id}",
        "minted_event_ref": None,
        "created_at": "2026-06-20T00:00:00+00:00",
        "not_before": "2026-06-20T00:00:00+00:00",
        "expires_at": "2099-06-20T00:15:00+00:00",
        "last_used_at": None,
        "revoked_at": None,
        "revoked_by": None,
        "revocation_reason": None,
    }


def _trip_constraint_breaker(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
    monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_THRESHOLD", 1)
    monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_WINDOW_SECONDS", 60)
    monkeypatch.setattr(anomaly, "QUARANTINE_WINDOW_SECONDS", 60)
    _write_lease(
        tmp_path,
        {
            **_v2_lease("lease-breaker", capabilities=["android.intent.send"]),
            "constraints": {"intent_actions": ["android.intent.action.VIEW"]},
        },
    )
    result = build_pre_tool_response(
        "android_intent_send",
        {
            "action": "android.intent.action.SEND",
            "package_name": "com.brave.browser",
            "dry_run": False,
        },
    )
    assert result is not None
    assert result["blocked"] is True
    assert "Security isolation triggered" in result["error_message"]


class TestAuthorityGatewayToolRegistration:
    def test_register_tools_callback_exposes_cockpit_surface(self):
        specs = register_callbacks.register_tools_callback()
        names = {spec["name"] for spec in specs}
        assert names == {
            "authority_gateway_status",
            "authority_gateway_list_active_leases",
            "authority_gateway_recent_audit",
            "authority_gateway_quarantine_status",
            "authority_gateway_release_quarantine",
            "authority_gateway_revoke_all",
        }

    def test_register_agent_tools_advertises_same_surface(self):
        advertised = register_callbacks._advertise_tools_to_agent("code-puppy")
        assert advertised == [
            "authority_gateway_status",
            "authority_gateway_list_active_leases",
            "authority_gateway_recent_audit",
            "authority_gateway_quarantine_status",
            "authority_gateway_release_quarantine",
            "authority_gateway_revoke_all",
        ]


class TestAuthorityGatewayTooling:
    def test_status_and_list_active_leases_show_live_state(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setattr(
            tooling,
            "_execution_topology_snapshot",
            lambda: {
                "success": True,
                "overall_status": "healthy",
                "deep_probe_ran": False,
                "ready_surface_count": 4,
                "blocked_surface_count": 3,
                "connected_adb_devices": 0,
                "ready_surface_ids": ["android_core", "browser_launch"],
                "blocked_surfaces": [
                    {
                        "surface_id": "browser_dom",
                        "blockers": ["no adb-connected Android device is available"],
                    }
                ],
                "capability_routes": [],
            },
        )
        _write_lease(tmp_path, _v2_lease("lease-one"))
        _write_lease(
            tmp_path,
            _v2_lease("lease-two", principal_id="worker-beta"),
        )

        status = tooling.authority_gateway_status()
        leases = tooling.authority_gateway_list_active_leases()
        filtered = tooling.authority_gateway_list_active_leases(
            principal_id="worker-beta"
        )

        assert status["success"] is True
        assert status["system_state"] == "armed"
        assert status["active_lease_count"] == 2
        assert status["quarantine_count"] == 0
        assert status["execution_topology"]["success"] is True
        assert status["execution_topology"]["ready_surface_count"] == 4
        assert status["execution_topology"]["blocked_surface_count"] == 3
        assert status["execution_topology"]["connected_adb_devices"] == 0
        assert "surface_ready=4" in status["summary"]
        assert "surface_blocked=3" in status["summary"]
        assert "adb_devices=0" in status["summary"]
        assert leases["count"] == 2
        assert filtered["count"] == 1
        assert filtered["leases"][0]["principal_id"] == "worker-beta"

    def test_status_degrades_gracefully_when_topology_snapshot_is_unavailable(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setattr(
            tooling,
            "_execution_topology_snapshot",
            lambda: {
                "success": False,
                "error": "droidpuppy_doctor unavailable: boom",
            },
        )

        status = tooling.authority_gateway_status()

        assert status["success"] is True
        assert status["system_state"] == "idle"
        assert status["execution_topology"]["success"] is False
        assert "surface_topology=unavailable" in status["summary"]

    def test_quarantine_status_and_recent_audit_surface_breaker_timeline(
        self, monkeypatch, tmp_path
    ):
        _trip_constraint_breaker(monkeypatch, tmp_path)

        status = tooling.authority_gateway_status()
        quarantines = tooling.authority_gateway_quarantine_status()
        audit_result = tooling.authority_gateway_recent_audit(limit=10)

        assert status["system_state"] == "contained"
        assert status["quarantine_count"] == 1
        assert status["recent_anomaly_count"] == 1
        assert quarantines["count"] == 1
        assert quarantines["quarantines"][0]["seconds_remaining"] > 0
        assert any("[BLOCKED]" in line for line in audit_result["lines"])
        assert any("[TRIPPED]" in line for line in audit_result["lines"])
        assert any("[REVOKED]" in line for line in audit_result["lines"])

    def test_release_quarantine_lifts_penalty_box_and_emits_audit(
        self, monkeypatch, tmp_path
    ):
        _trip_constraint_breaker(monkeypatch, tmp_path)
        principal_id = get_default_principal_id()

        before = anomaly.active_quarantine_reason(principal_id=principal_id)
        release = tooling.authority_gateway_release_quarantine(
            principal_id=principal_id,
            reason="operator fixed the loop",
            released_by="butcher",
        )
        after = anomaly.active_quarantine_reason(principal_id=principal_id)
        audit_result = tooling.authority_gateway_recent_audit(limit=10)

        assert before is not None
        assert release["success"] is True
        assert release["released"] is True
        assert release["released_by"] == "butcher"
        assert after is None
        assert any("[RELEASED]" in line for line in audit_result["lines"])

        events = [
            json.loads(path.read_text())
            for path in sorted((tmp_path / "audit" / "events").glob("*.json"))
        ]
        assert events[-1]["event_type"] == "quarantine_released"
        assert events[-1]["details"]["released_by"] == "butcher"

    def test_revoke_all_vaporizes_every_active_lease(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        lease_one = _write_lease(tmp_path, _v2_lease("lease-one"))
        lease_two = _write_lease(tmp_path, _v2_lease("lease-two"))

        result = tooling.authority_gateway_revoke_all(
            reason="operator hit the red button",
            revoked_by="butcher",
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert sorted(result["lease_ids"]) == ["lease-one", "lease-two"]
        assert json.loads(lease_one.read_text())["status"] == "revoked"
        assert json.loads(lease_two.read_text())["status"] == "revoked"

        events = [
            json.loads(path.read_text())
            for path in sorted((tmp_path / "audit" / "events").glob("*.json"))
        ]
        kinds = [event["event_type"] for event in events]
        assert kinds.count("lease_revoked") == 2
        assert kinds[-1] == "leases_revoked"
