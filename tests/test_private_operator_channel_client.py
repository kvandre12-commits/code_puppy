from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

from code_puppy.plugins.private_operator_channel.config import load_private_operator_channel_config
from code_puppy.plugins.private_operator_channel.runtime import PrivateOperatorChannelRuntime
from code_puppy.plugins.private_operator_channel.server import build_http_server, build_ssl_context

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SCRIPT = ROOT / "scripts" / "private_operator_channel_client.py"


def test_build_ssl_context_returns_none_when_tls_disabled_config() -> None:
    from code_puppy.plugins.private_operator_channel.config import (
        PrivateOperatorChannelConfig,
    )

    assert build_ssl_context(PrivateOperatorChannelConfig()) is None


def test_build_ssl_context_requires_cert_and_key_when_enabled() -> None:
    from code_puppy.plugins.private_operator_channel.config import (
        PrivateOperatorChannelConfig,
    )

    config = PrivateOperatorChannelConfig(tls_enabled=True)
    try:
        build_ssl_context(config)
    except ValueError as exc:
        assert "tls_certfile" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing TLS files")


def test_private_operator_channel_client_round_trip(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "private_channel.json"
    config_path.write_text(
        json.dumps(
            {
                "bind_host": "127.0.0.1",
                "port": 0,
                "allow_effectful_actions": False,
                "allowed_actions": ["status"],
                "allowed_android_targets": ["wifi"],
                "shared_secret_env": "PRIVATE_OPERATOR_CHANNEL_SECRET",
                "audit_log_path": str(tmp_path / "audit.jsonl"),
                "tls_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRIVATE_OPERATOR_CHANNEL_SECRET", "secret-client")
    monkeypatch.setattr(
        "code_puppy.plugins.private_operator_channel.runtime.authority_gateway_status",
        lambda: {"success": True, "summary": "authority-ok"},
    )
    monkeypatch.setattr(
        "code_puppy.plugins.private_operator_channel.runtime.project_os_bus_status",
        lambda timeout_seconds=0.25: {"success": True, "timeout_seconds": timeout_seconds},
    )

    config, resolved_path, config_exists = load_private_operator_channel_config(
        str(config_path)
    )
    runtime = PrivateOperatorChannelRuntime(
        config=config,
        config_path=resolved_path,
        config_exists=config_exists,
    )
    server = build_http_server(config=config, runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        result = subprocess.run(
            [
                sys.executable,
                str(CLIENT_SCRIPT),
                "--url",
                f"http://{host}:{port}/v1/control",
                "--action",
                "status",
                "--args-json",
                '{"include_authority": true, "include_bus": true}',
                "--shared-secret",
                "secret-client",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["authority_gateway"]["summary"] == "authority-ok"
        assert payload["project_os_bus"]["success"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
