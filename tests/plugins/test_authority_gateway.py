from __future__ import annotations

import json
from pathlib import Path

from code_puppy.plugins.authority_gateway import anomaly, audit
from code_puppy.plugins.authority_gateway.audit import revoke_all_leases_with_audit
from code_puppy.plugins.authority_gateway.identity import bind_runtime_actor_context
from code_puppy.plugins.authority_gateway.lease_store import (
    consume_lease,
    find_matching_lease,
    get_default_principal_id,
)
from code_puppy.plugins.authority_gateway.policy import (
    assess_shell_command,
    build_pre_tool_response,
    evaluate_tool_call,
    handle_post_tool_result,
    reservation_debug_state,
)


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
    allowed_tools: list[str] | None = None,
    constraints: dict | None = None,
    delegation: dict | None = None,
    remaining_uses: int = 1,
    max_uses: int = 1,
    max_tool_calls: int | None = None,
    max_shell_commands: int | None = None,
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
        "allowed_tools": allowed_tools or [],
        "constraints": constraints or {},
        "delegation": delegation
        or {
            "mode": "direct",
            "requested_by_actor_id": None,
            "delegated_by_actor_id": None,
            "delegated_to_actor_ids": [],
            "run_id": None,
        },
        "quotas": {
            "max_uses": max_uses,
            "remaining_uses": remaining_uses,
            "max_tool_calls": max_tool_calls,
            "max_shell_commands": max_shell_commands,
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


class TestShellAuthorityPolicy:
    def test_safe_shell_command_is_allowed_without_lease(self):
        decision = assess_shell_command("git status")
        assert not decision.blocked
        assert not decision.lease_required

    def test_dangerous_shell_command_is_blocked(self):
        decision = assess_shell_command("rm -rf /tmp/nope")
        assert decision.blocked
        assert "forbidden shell pattern" in decision.reason

    def test_non_allowlisted_shell_command_requires_process_lease(self):
        decision = assess_shell_command("npm install")
        assert not decision.blocked
        assert decision.lease_required
        assert decision.capability == "shell.process.exec"

    def test_workspace_shell_command_requires_repo_write_lease(self):
        decision = assess_shell_command("npm install", cwd=str(Path.cwd()))
        assert not decision.blocked
        assert decision.lease_required
        assert decision.capability == "shell.repo.write"

    def test_network_shell_command_requires_network_lease(self):
        decision = assess_shell_command("ssh 192.168.1.8")
        assert not decision.blocked
        assert decision.lease_required
        assert decision.capability == "network.lan.connect"

    def test_adb_shell_command_requires_wireless_debug_lease(self):
        decision = assess_shell_command("adb connect 192.168.1.2:5555")
        assert not decision.blocked
        assert decision.lease_required
        assert decision.capability == "adb.wireless.connect"


class TestAndroidPolicy:
    def test_intent_dry_run_is_allowed(self):
        decision = evaluate_tool_call(
            "android_intent_send",
            {
                "action": "android.intent.action.VIEW",
                "data_uri": "https://example.com",
                "dry_run": True,
            },
        )
        assert not decision.blocked
        assert not decision.lease_required

    def test_broadcast_intent_is_statically_blocked(self):
        decision = evaluate_tool_call(
            "android_intent_send",
            {
                "action": "android.intent.action.VIEW",
                "dispatch_mode": "broadcast",
                "dry_run": False,
            },
        )
        assert decision.blocked
        assert "Broadcast intents" in decision.reason

    def test_live_android_open_rejects_unknown_shortcut(self):
        decision = evaluate_tool_call(
            "android_open",
            {"target": "com.totally.unknown.app", "browser": "brave", "dry_run": False},
        )
        assert decision.blocked
        assert "built-in shortcut targets" in decision.reason

    def test_live_handoff_file_outside_outputs_is_blocked(self):
        decision = evaluate_tool_call(
            "android_handoff_file",
            {"file_path": "README.md", "dry_run": False},
        )
        assert decision.blocked
        assert "outputs/ directory" in decision.reason


class TestLeaseBinding:
    def test_live_tool_blocks_without_matching_lease(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        result = build_pre_tool_response("android_open_settings", {"page": "wifi"})
        assert result is not None
        assert result["blocked"] is True
        assert "active execution lease" in result["error_message"]

        events = sorted((tmp_path / "audit" / "events").glob("*.json"))
        assert len(events) == 1
        payload = json.loads(events[0].read_text())
        assert payload["event_type"] == "tool_blocked"

    def test_v2_lease_allows_settings_open_and_consumes_use(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        lease_path = _write_lease(
            tmp_path,
            _v2_lease(
                "lease-123",
                capabilities=["android.settings.open"],
                remaining_uses=1,
            ),
        )

        pre = build_pre_tool_response("android_open_settings", {"page": "wifi"})
        assert pre is None
        assert reservation_debug_state()["lease_id"] == "lease-123"

        handle_post_tool_result("android_open_settings", {"success": True})
        payload = json.loads(lease_path.read_text())
        assert payload["quotas"]["remaining_uses"] == 0
        assert payload["status"] == "used"
        assert reservation_debug_state()["lease_id"] is None

        events = sorted((tmp_path / "audit" / "events").glob("*.json"))
        assert [json.loads(path.read_text())["event_type"] for path in events] == [
            "tool_allowed",
            "lease_consumed",
        ]

    def test_capability_specific_lease_matches_tool(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        _write_lease(tmp_path, _v2_lease("lease-cap", capabilities=["shell.exec"]))

        record = find_matching_lease(
            capability="shell.repo.write",
            tool_name="agent_run_shell_command",
            principal_id=get_default_principal_id(),
        )
        assert record is not None
        assert record.lease_id == "lease-cap"

    def test_allowed_tools_becomes_real_restriction(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-tool-lock",
                capabilities=["android.browser.open_url"],
                allowed_tools=["android_browser_open_url"],
            ),
        )

        blocked = build_pre_tool_response(
            "android_open",
            {"target": "https://example.com", "browser": "brave"},
        )
        assert blocked is not None
        assert blocked["blocked"] is True

        allowed = build_pre_tool_response(
            "android_browser_open_url",
            {"url": "https://example.com", "browser": "brave"},
        )
        assert allowed is None

    def test_failed_result_does_not_consume_reserved_lease(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        lease_path = _write_lease(tmp_path, _v2_lease("lease-stays"))

        pre = build_pre_tool_response(
            "agent_run_shell_command", {"command": "npm install"}
        )
        assert pre is None
        handle_post_tool_result("agent_run_shell_command", {"success": False})
        payload = json.loads(lease_path.read_text())
        assert payload["quotas"]["remaining_uses"] == 1
        assert payload["status"] == "active"

        events = sorted((tmp_path / "audit" / "events").glob("*.json"))
        assert [json.loads(path.read_text())["event_type"] for path in events] == [
            "tool_allowed",
            "tool_failed",
        ]

    def test_principal_mismatch_blocks_lease_usage(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        _write_lease(
            tmp_path,
            _v2_lease("lease-other", principal_id="some-other-agent"),
        )

        result = build_pre_tool_response(
            "agent_run_shell_command", {"command": "npm install"}
        )
        assert result is not None
        assert result["blocked"] is True

    def test_stable_authority_principal_survives_actor_rotation(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setenv("PROJECT_OS_AUTHORITY_PRINCIPAL_ID", "stable-authority")
        lease_path = _write_lease(
            tmp_path,
            _v2_lease(
                "lease-stable",
                principal_id="stable-authority",
                capabilities=["shell.repo.write"],
                delegation={
                    "mode": "shared_authority",
                    "requested_by_actor_id": "code-puppy-main",
                    "delegated_by_actor_id": "code-puppy-main",
                    "delegated_to_actor_ids": ["code-puppy-subagent"],
                    "run_id": "run-sub-1",
                },
            ),
        )

        with bind_runtime_actor_context(
            actor_id="code-puppy-subagent", run_id="run-sub-1"
        ):
            allowed = build_pre_tool_response(
                "agent_run_shell_command",
                {"command": "npm install", "cwd": str(tmp_path)},
            )
            assert allowed is None
            handle_post_tool_result("agent_run_shell_command", {"success": True})

        payload = json.loads(lease_path.read_text())
        assert payload["quotas"]["shell_commands_used"] == 1
        assert payload["principal_id"] == "stable-authority"

        events = [
            json.loads(path.read_text())
            for path in sorted((tmp_path / "audit" / "events").glob("*.json"))
        ]
        assert events[0]["principal_id"] == "stable-authority"
        assert events[0]["details"]["actor_id"] == "code-puppy-subagent"
        assert events[0]["details"]["run_id"] == "run-sub-1"

    def test_intent_constraints_allow_only_approved_action_and_package(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-intent",
                capabilities=["android.intent.send"],
                constraints={
                    "intent_actions": ["android.intent.action.VIEW"],
                    "intent_packages": ["com.brave.browser"],
                },
            ),
        )

        denied = build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.SEND",
                "package_name": "com.brave.browser",
                "dry_run": False,
            },
        )
        assert denied is not None
        assert denied["blocked"] is True
        assert "specific Android intent actions" in denied["error_message"]

        allowed = build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.VIEW",
                "package_name": "com.brave.browser",
                "data_uri": "https://example.com",
                "dry_run": False,
            },
        )
        assert allowed is None

    def test_browser_constraint_blocks_wrong_browser(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-browser",
                capabilities=["android.browser.open_url"],
                constraints={"browser_packages": ["chrome"]},
            ),
        )

        denied = build_pre_tool_response(
            "android_browser_open_url",
            {"url": "https://example.com", "browser": "brave"},
        )
        assert denied is not None
        assert denied["blocked"] is True
        assert "specific browser packages" in denied["error_message"]

        allowed = build_pre_tool_response(
            "android_browser_open_url",
            {"url": "https://example.com", "browser": "chrome"},
        )
        assert allowed is None

    def test_path_locked_handoff_only_allows_approved_directory(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        allowed_dir = tmp_path / "outputs" / "leases"
        allowed_dir.mkdir(parents=True, exist_ok=True)
        allowed_file = allowed_dir / "ok.txt"
        allowed_file.write_text("hi")
        denied_file = tmp_path / "outputs" / "other" / "no.txt"
        denied_file.parent.mkdir(parents=True, exist_ok=True)
        denied_file.write_text("no")

        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-path",
                capabilities=["android.handoff.share"],
                constraints={"allowed_paths": [str(allowed_dir)]},
            ),
        )

        denied = build_pre_tool_response(
            "android_handoff_file",
            {"file_path": str(denied_file), "dry_run": False},
        )
        assert denied is not None
        assert denied["blocked"] is True
        assert "approved paths" in denied["error_message"]

        allowed = build_pre_tool_response(
            "android_handoff_file",
            {"file_path": str(allowed_file), "dry_run": False},
        )
        assert allowed is None

    def test_path_locked_shell_requires_cwd_inside_constraint(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        allowed_dir = tmp_path / "sandbox"
        allowed_dir.mkdir()
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-shell-path",
                capabilities=["shell.repo.write"],
                constraints={"allowed_paths": [str(allowed_dir)]},
            ),
        )

        denied = build_pre_tool_response(
            "agent_run_shell_command",
            {"command": "npm install", "cwd": str(tmp_path)},
        )
        assert denied is not None
        assert denied["blocked"] is True
        assert "shell execution within approved paths" in denied["error_message"]

        allowed = build_pre_tool_response(
            "agent_run_shell_command",
            {"command": "npm install", "cwd": str(allowed_dir)},
        )
        assert allowed is None

    def test_repeated_constraint_violations_trip_circuit_breaker(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_THRESHOLD", 3)
        monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_WINDOW_SECONDS", 60)
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-breaker",
                capabilities=["android.intent.send"],
                constraints={
                    "intent_actions": ["android.intent.action.VIEW"],
                    "intent_packages": ["com.brave.browser"],
                },
            ),
        )

        result = None
        for _ in range(3):
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

        lease_payload = json.loads(
            (tmp_path / "leases" / "active" / "lease-breaker.json").read_text()
        )
        assert lease_payload["status"] == "revoked"
        assert "constraint violations" in lease_payload["revocation_reason"]

        events = [
            json.loads(path.read_text())
            for path in sorted((tmp_path / "audit" / "events").glob("*.json"))
        ]
        kinds = [event["event_type"] for event in events]
        assert kinds.count("tool_blocked") == 3
        assert "anomaly_detected" in kinds
        assert "lease_revoked" in kinds
        assert "leases_revoked" in kinds

    def test_runaway_shell_loop_trips_circuit_breaker(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setattr(anomaly, "RUNAWAY_ATTEMPT_THRESHOLD", 3)
        monkeypatch.setattr(anomaly, "RUNAWAY_ATTEMPT_WINDOW_SECONDS", 60)
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-runaway",
                capabilities=["shell.repo.write"],
                remaining_uses=5,
                max_uses=5,
                max_tool_calls=5,
            ),
        )

        first = build_pre_tool_response(
            "agent_run_shell_command", {"command": "npm install", "cwd": str(tmp_path)}
        )
        second = build_pre_tool_response(
            "agent_run_shell_command", {"command": "npm install", "cwd": str(tmp_path)}
        )
        third = build_pre_tool_response(
            "agent_run_shell_command", {"command": "npm install", "cwd": str(tmp_path)}
        )

        assert first is None
        assert second is None
        assert third is not None
        assert third["blocked"] is True
        assert "runaway shell/intent execution loop" in third["error_message"]
        assert reservation_debug_state()["lease_id"] is None

        lease_payload = json.loads(
            (tmp_path / "leases" / "active" / "lease-runaway.json").read_text()
        )
        assert lease_payload["status"] == "revoked"

        events = [
            json.loads(path.read_text())
            for path in sorted((tmp_path / "audit" / "events").glob("*.json"))
        ]
        kinds = [event["event_type"] for event in events]
        assert kinds.count("tool_allowed") == 3
        assert "anomaly_detected" in kinds
        assert "lease_revoked" in kinds
        assert "leases_revoked" in kinds

    def test_quarantine_blocks_follow_up_attempts_after_breaker(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_THRESHOLD", 2)
        monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_WINDOW_SECONDS", 60)
        monkeypatch.setattr(anomaly, "QUARANTINE_WINDOW_SECONDS", 60)
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-quarantine",
                capabilities=["android.intent.send"],
                constraints={
                    "intent_actions": ["android.intent.action.VIEW"],
                    "intent_packages": ["com.brave.browser"],
                },
            ),
        )

        build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.SEND",
                "package_name": "com.brave.browser",
                "dry_run": False,
            },
        )
        tripped = build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.SEND",
                "package_name": "com.brave.browser",
                "dry_run": False,
            },
        )
        quarantined = build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.VIEW",
                "package_name": "com.brave.browser",
                "dry_run": False,
            },
        )

        assert tripped is not None
        assert "Security isolation triggered" in tripped["error_message"]
        assert quarantined is not None
        assert quarantined["blocked"] is True
        assert "Principal is quarantined" in quarantined["error_message"]

        events = [
            json.loads(path.read_text())
            for path in sorted((tmp_path / "audit" / "events").glob("*.json"))
        ]
        assert events[-1]["event_type"] == "tool_blocked"
        assert events[-1]["details"]["block_kind"] == "quarantine"

    def test_quarantine_expiry_falls_back_to_normal_policy(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_THRESHOLD", 1)
        monkeypatch.setattr(anomaly, "CONSTRAINT_BLOCK_WINDOW_SECONDS", 1)
        monkeypatch.setattr(anomaly, "QUARANTINE_WINDOW_SECONDS", 1)
        _write_lease(
            tmp_path,
            _v2_lease(
                "lease-expiry",
                capabilities=["android.intent.send"],
                constraints={"intent_actions": ["android.intent.action.VIEW"]},
            ),
        )

        triggered = build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.SEND",
                "package_name": "com.brave.browser",
                "dry_run": False,
            },
        )
        assert triggered is not None
        assert "Security isolation triggered" in triggered["error_message"]

        original_time_ns = audit.time.time_ns
        monkeypatch.setattr(
            audit.time,
            "time_ns",
            lambda: original_time_ns() + 2_000_000_000,
        )

        after_expiry = build_pre_tool_response(
            "android_intent_send",
            {
                "action": "android.intent.action.VIEW",
                "package_name": "com.brave.browser",
                "dry_run": False,
            },
        )
        assert after_expiry is not None
        assert after_expiry["blocked"] is True
        assert "active execution lease" in after_expiry["error_message"]


class TestLeaseStoreHelpers:
    def test_consume_lease_marks_used(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        lease_path = _write_lease(
            tmp_path,
            _v2_lease("lease-helper", capabilities=["shell.repo.write"]),
        )
        record = find_matching_lease(
            capability="shell.repo.write",
            tool_name="agent_run_shell_command",
            principal_id=get_default_principal_id(),
        )
        assert record is not None
        consume_lease(
            record,
            capability="shell.repo.write",
            tool_name="agent_run_shell_command",
        )
        payload = json.loads(lease_path.read_text())
        assert payload["quotas"]["remaining_uses"] == 0
        assert payload["quotas"]["tool_calls_used"] == 1
        assert payload["quotas"]["shell_commands_used"] == 1
        assert payload["status"] == "used"

    def test_revoke_all_leases_with_audit(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path))
        lease_path = _write_lease(tmp_path, _v2_lease("lease-revoke"))

        revoked = revoke_all_leases_with_audit(
            "loop detected",
            revoked_by="watchdog",
            principal_id=get_default_principal_id(),
        )
        assert len(revoked) == 1

        payload = json.loads(lease_path.read_text())
        assert payload["status"] == "revoked"
        assert payload["revocation_reason"] == "loop detected"
        assert payload["revoked_by"] == "watchdog"

        events = sorted((tmp_path / "audit" / "events").glob("*.json"))
        kinds = [json.loads(path.read_text())["event_type"] for path in events]
        assert kinds == ["lease_revoked", "leases_revoked"]
