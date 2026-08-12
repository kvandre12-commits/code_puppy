from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from code_puppy.plugins.private_operator_channel.config import (
    load_private_operator_channel_config,
    write_example_config,
)
from code_puppy.plugins.authority_gateway.lease_store import mint_lease
from code_puppy.plugins.private_operator_channel.runtime import (
    PrivateOperatorChannelRuntime,
    build_signed_request,
)
from code_puppy.plugins.private_operator_channel.server import build_http_server


def test_write_example_config_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "private_channel.json"
    result = write_example_config(str(config_path), overwrite=False)
    assert result["success"] is True

    config, resolved_path, config_exists = load_private_operator_channel_config(
        str(config_path)
    )
    assert config_exists is True
    assert resolved_path == config_path.resolve()
    assert config.port == 8766
    assert config.tls_enabled is False
    assert config.require_client_certificate is False
    assert "status" in config.allowed_actions
    assert "android_open" in config.allowed_actions


def test_runtime_rejects_effectful_android_open_when_disabled(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "private_channel.json"
    write_example_config(str(config_path), overwrite=True)
    config, resolved_path, config_exists = load_private_operator_channel_config(
        str(config_path)
    )
    runtime = PrivateOperatorChannelRuntime(
        config=config,
        config_path=resolved_path,
        config_exists=config_exists,
    )
    monkeypatch.setenv(config.shared_secret_env, "secret-123")
    payload = build_signed_request(
        action="android_open",
        args={"target": "wifi", "dry_run": False},
        shared_secret="secret-123",
    )
    status_code, result = runtime.handle_payload(payload)
    assert status_code == 403
    assert result["error"] == "effectful_actions_disabled"


def test_runtime_requires_lease_for_effectful_android_open(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "private_channel.json"
    config_path.write_text(
        json.dumps(
            {
                "bind_host": "127.0.0.1",
                "port": 0,
                "allow_effectful_actions": True,
                "allowed_actions": ["android_open"],
                "allowed_android_targets": ["wifi"],
                "shared_secret_env": "PRIVATE_OPERATOR_CHANNEL_SECRET",
                "audit_log_path": str(tmp_path / "audit.jsonl"),
                "require_governance_for_effectful_actions": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRIVATE_OPERATOR_CHANNEL_SECRET", "secret-lease")
    config, resolved_path, config_exists = load_private_operator_channel_config(
        str(config_path)
    )
    runtime = PrivateOperatorChannelRuntime(
        config=config,
        config_path=resolved_path,
        config_exists=config_exists,
    )
    payload = build_signed_request(
        action="android_open",
        args={"target": "wifi", "dry_run": False},
        shared_secret="secret-lease",
    )
    status_code, result = runtime.handle_payload(payload)
    assert status_code == 403
    assert result["error"] == "missing_lease_id"
    assert result["required_capability"] == "android.settings.open"


def test_runtime_consumes_matching_lease_for_effectful_android_open(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(tmp_path / "eyes"))
    monkeypatch.setenv("PRIVATE_OPERATOR_CHANNEL_SECRET", "secret-lease")
    config_path = tmp_path / "private_channel.json"
    config_path.write_text(
        json.dumps(
            {
                "bind_host": "127.0.0.1",
                "port": 0,
                "allow_effectful_actions": True,
                "allowed_actions": ["android_open"],
                "allowed_android_targets": ["wifi"],
                "shared_secret_env": "PRIVATE_OPERATOR_CHANNEL_SECRET",
                "audit_log_path": str(tmp_path / "audit.jsonl"),
                "require_governance_for_effectful_actions": True,
            }
        ),
        encoding="utf-8",
    )
    config, resolved_path, config_exists = load_private_operator_channel_config(
        str(config_path)
    )
    runtime = PrivateOperatorChannelRuntime(
        config=config,
        config_path=resolved_path,
        config_exists=config_exists,
    )
    monkeypatch.setattr(
        "code_puppy.plugins.private_operator_channel.runtime.android_open",
        lambda target, browser="brave", dry_run=False: {
            "success": True,
            "target": target,
            "browser": browser,
            "dry_run": dry_run,
        },
    )
    lease = mint_lease(
        principal_id="code-puppy-41abae",
        capabilities=["android.settings.open"],
        reason="test effectful private channel open",
        granted_by="operator",
        allowed_tools=["android_open"],
        constraints={},
        ttl_seconds=300,
        max_uses=2,
    )
    payload = build_signed_request(
        action="android_open",
        args={"target": "wifi", "dry_run": False, "lease_id": lease.lease_id},
        shared_secret="secret-lease",
    )
    status_code, result = runtime.handle_payload(payload)
    assert status_code == 200
    assert result["success"] is True
    assert result["lease_id"] == lease.lease_id
    assert result["required_capability"] == "android.settings.open"
    assert result["remaining_uses"] == 1


def test_http_server_status_round_trip(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "private_channel.json"
    config_path.write_text(
        json.dumps(
            {
                "bind_host": "127.0.0.1",
                "port": 0,
                "allow_effectful_actions": False,
                "allowed_actions": ["status", "ping"],
                "allowed_android_targets": ["wifi"],
                "shared_secret_env": "PRIVATE_OPERATOR_CHANNEL_SECRET",
                "audit_log_path": str(tmp_path / "audit.jsonl"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRIVATE_OPERATOR_CHANNEL_SECRET", "secret-xyz")
    config, resolved_path, config_exists = load_private_operator_channel_config(
        str(config_path)
    )
    runtime = PrivateOperatorChannelRuntime(
        config=config,
        config_path=resolved_path,
        config_exists=config_exists,
    )
    monkeypatch.setattr(
        "code_puppy.plugins.private_operator_channel.runtime.authority_gateway_status",
        lambda: {"success": True, "summary": "authority-ok"},
    )
    monkeypatch.setattr(
        "code_puppy.plugins.private_operator_channel.runtime.project_os_bus_status",
        lambda timeout_seconds=0.25: {
            "success": True,
            "timeout_seconds": timeout_seconds,
        },
    )

    server = build_http_server(config=config, runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        payload = build_signed_request(
            action="status",
            args={"include_authority": True, "include_bus": True},
            shared_secret="secret-xyz",
        )
        request = urllib.request.Request(
            url=f"http://{host}:{port}/v1/control",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["authority_gateway"]["summary"] == "authority-ok"
        assert body["project_os_bus"]["success"] is True
        assert Path(tmp_path / "audit.jsonl").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
