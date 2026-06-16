import asyncio
import stat
import time
from types import SimpleNamespace

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from code_puppy.plugins.mcp_oauth import config as oauth_config
from code_puppy.plugins.mcp_oauth.oauth_flow import parse_callback_input
from code_puppy.plugins.mcp_oauth.register_callbacks import (
    _apply_runtime_bearer,
    _pre_mcp_autostart,
)
from code_puppy.plugins.mcp_oauth.storage import ServerTokenStorage


def test_get_server_settings_normalizes_values(monkeypatch):
    monkeypatch.setenv("MCP_TEST_KEY", "sekret")
    monkeypatch.setattr(
        oauth_config.app_config,
        "load_mcp_server_configs",
        lambda: {
            "robinhood": {
                "type": "http",
                "url": "https://example.com/mcp",
                "headers": {"X-Api-Key": "$MCP_TEST_KEY"},
                "oauth": {
                    "enabled": True,
                    "scopes": ["openid", "profile"],
                    "manual_callback_only": "true",
                    "auto_authorize_on_autostart": "false",
                    "callback_timeout": "123",
                    "expiry_buffer_seconds": "45",
                },
            }
        },
    )

    settings = oauth_config.get_server_settings("robinhood")

    assert settings is not None
    assert settings.server_type == "http"
    assert settings.scope == "openid profile"
    assert settings.manual_callback_only is True
    assert settings.auto_authorize_on_autostart is False
    assert settings.callback_timeout == 123
    assert settings.expiry_buffer_seconds == 45
    assert settings.base_headers["X-Api-Key"] == "sekret"


def test_server_token_storage_marks_expired_token_for_refresh(tmp_path, monkeypatch):
    token_path = tmp_path / "robinhood.json"
    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.storage.get_token_storage_path",
        lambda server_name: token_path,
    )

    storage = ServerTokenStorage("robinhood", expiry_buffer_seconds=30)
    storage.save_state(
        {
            "tokens": {
                "access_token": "old-token",
                "refresh_token": "refresh-me",
                "token_type": "Bearer",
                "expires_in": 3600,
                "expires_at": time.time() - 5,
            }
        }
    )

    token = asyncio.run(storage.get_tokens())

    assert token is not None
    assert token.access_token == ""
    assert token.refresh_token == "refresh-me"
    assert token.expires_in == 0


def test_server_token_storage_persists_private_permissions(tmp_path, monkeypatch):
    token_path = tmp_path / "nested" / "robinhood.json"
    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.storage.get_token_storage_path",
        lambda server_name: token_path,
    )

    storage = ServerTokenStorage("robinhood")
    storage.save_state({"tokens": {"access_token": "x"}})

    dir_mode = stat.S_IMODE(token_path.parent.stat().st_mode)
    file_mode = stat.S_IMODE(token_path.stat().st_mode)

    assert dir_mode == 0o700
    assert file_mode == 0o600


def test_server_token_storage_round_trips_client_info(tmp_path, monkeypatch):
    token_path = tmp_path / "robinhood.json"
    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.storage.get_token_storage_path",
        lambda server_name: token_path,
    )

    storage = ServerTokenStorage("robinhood")
    client_info = OAuthClientInformationFull(
        client_id="client-123",
        token_endpoint_auth_method="none",
        redirect_uris=["http://127.0.0.1:8765/auth/callback"],
    )
    asyncio.run(storage.set_client_info(client_info))
    asyncio.run(
        storage.set_tokens(
            OAuthToken(
                access_token="access-123",
                refresh_token="refresh-123",
                expires_in=120,
                token_type="Bearer",
            )
        )
    )

    loaded_client_info = asyncio.run(storage.get_client_info())
    loaded_token = asyncio.run(storage.get_tokens())

    assert loaded_client_info is not None
    assert loaded_client_info.client_id == "client-123"
    assert loaded_token is not None
    assert loaded_token.access_token == "access-123"


def test_parse_callback_input_variants():
    assert parse_callback_input("") == (None, None)
    assert parse_callback_input("code123 state456") == ("code123", "state456")
    assert parse_callback_input("code123#state456") == ("code123", "state456")
    assert parse_callback_input("https://x.test/cb?code=a1&state=b2") == ("a1", "b2")


class _FakeManagedServer:
    def __init__(self, *, running=False):
        self.config = None
        self._pydantic_server = SimpleNamespace(is_running=running)
        self.create_calls = 0
        self.running = running

    def _create_server(self):
        self.create_calls += 1
        self._pydantic_server = SimpleNamespace(is_running=self.running)

    def get_status(self):
        return {"server_available": self.running, "state": "running" if self.running else "stopped"}


class _FakeManager:
    def __init__(self, *, running=False):
        self.registry_config = SimpleNamespace(
            id="srv-1",
            name="robinhood",
            type="http",
            enabled=True,
            config={"url": "https://example.com/mcp", "headers": {"X-Test": "1"}},
        )
        self.managed = _FakeManagedServer(running=running)

    def get_server_by_name(self, name):
        assert name == "robinhood"
        return self.registry_config

    def get_server(self, server_id):
        assert server_id == "srv-1"
        return self.managed


def test_pre_mcp_autostart_injects_runtime_bearer(monkeypatch):
    fake_manager = _FakeManager()
    fake_settings = oauth_config.OAuthServerSettings(
        server_name="robinhood",
        server_type="http",
        server_url="https://example.com/mcp",
        scope=None,
        client_name="Code Puppy MCP OAuth",
        client_metadata_url=None,
        client_id=None,
        client_secret=None,
        token_endpoint_auth_method=None,
        redirect_host="http://127.0.0.1",
        callback_path="/auth/callback",
        callback_port_range=(8765, 8795),
        callback_timeout=300,
        auto_authorize_on_autostart=True,
        manual_callback_only=False,
        protocol_version="2025-06-18",
        expiry_buffer_seconds=60,
        base_headers={},
    )

    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.register_callbacks.get_server_settings",
        lambda name: fake_settings if name == "robinhood" else None,
    )
    async def _fake_ensure_access_token(settings, allow_interactive, force_reauth):
        del settings, allow_interactive, force_reauth
        return "token-xyz"

    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.register_callbacks.ensure_access_token",
        _fake_ensure_access_token,
    )
    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.register_callbacks.get_mcp_manager",
        lambda: fake_manager,
    )

    asyncio.run(_pre_mcp_autostart("main-agent", ["robinhood"]))

    assert fake_manager.managed.create_calls == 1
    assert fake_manager.managed.config.config["headers"]["Authorization"] == "Bearer token-xyz"
    assert fake_manager.managed.config.config["headers"]["X-Test"] == "1"


def test_apply_runtime_bearer_refuses_running_server(monkeypatch):
    fake_manager = _FakeManager(running=True)
    fake_settings = oauth_config.OAuthServerSettings(
        server_name="robinhood",
        server_type="http",
        server_url="https://example.com/mcp",
        scope=None,
        client_name="Code Puppy MCP OAuth",
        client_metadata_url=None,
        client_id=None,
        client_secret=None,
        token_endpoint_auth_method=None,
        redirect_host="http://127.0.0.1",
        callback_path="/auth/callback",
        callback_port_range=(8765, 8795),
        callback_timeout=300,
        auto_authorize_on_autostart=True,
        manual_callback_only=False,
        protocol_version="2025-06-18",
        expiry_buffer_seconds=60,
        base_headers={},
    )
    warnings = []

    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.register_callbacks.get_server_settings",
        lambda name: fake_settings if name == "robinhood" else None,
    )
    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.register_callbacks.get_mcp_manager",
        lambda: fake_manager,
    )
    monkeypatch.setattr(
        "code_puppy.plugins.mcp_oauth.register_callbacks.emit_warning",
        lambda message: warnings.append(message),
    )

    ok = asyncio.run(_apply_runtime_bearer("robinhood", "token-xyz"))

    assert ok is False
    assert fake_manager.managed.create_calls == 0
    assert warnings
    assert "already running" in warnings[0]
