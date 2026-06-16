"""Configuration helpers for the MCP OAuth plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from code_puppy import config as app_config

DEFAULT_CALLBACK_PORT_RANGE = (8765, 8795)
DEFAULT_CALLBACK_TIMEOUT = 300
DEFAULT_CALLBACK_PATH = "/auth/callback"
DEFAULT_REDIRECT_HOST = "http://127.0.0.1"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_CLIENT_NAME = "Code Puppy MCP OAuth"
DEFAULT_EXPIRY_BUFFER_SECONDS = 60


@dataclass(frozen=True)
class OAuthServerSettings:
    """Resolved OAuth settings for one MCP server."""

    server_name: str
    server_type: str
    server_url: str
    scope: Optional[str]
    client_name: str
    client_metadata_url: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    token_endpoint_auth_method: Optional[str]
    redirect_host: str
    callback_path: str
    callback_port_range: Tuple[int, int]
    callback_timeout: int
    auto_authorize_on_autostart: bool
    manual_callback_only: bool
    protocol_version: str
    expiry_buffer_seconds: int
    base_headers: Dict[str, str]

    @property
    def callback_bind_host(self) -> str:
        parsed = urlparse(self.redirect_host)
        return parsed.hostname or "127.0.0.1"


def get_oauth_storage_dir() -> Path:
    path = Path(app_config.DATA_DIR) / "mcp_oauth"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slugify_server_name(server_name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in server_name)
    safe = safe.strip("_")
    return safe or "server"


def get_token_storage_path(server_name: str) -> Path:
    return get_oauth_storage_dir() / f"{_slugify_server_name(server_name)}.json"


def load_mcp_server_map() -> Dict[str, Dict[str, Any]]:
    return app_config.load_mcp_server_configs() or {}


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_scope(oauth_config: Dict[str, Any]) -> Optional[str]:
    scope = oauth_config.get("scope")
    if isinstance(scope, str) and scope.strip():
        return scope.strip()

    scopes = oauth_config.get("scopes")
    if isinstance(scopes, str) and scopes.strip():
        return scopes.strip()
    if isinstance(scopes, list):
        parts = [str(item).strip() for item in scopes if str(item).strip()]
        return " ".join(parts) or None
    return None


def _normalize_port_range(raw: Any) -> Tuple[int, int]:
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        try:
            start = int(raw[0])
            end = int(raw[1])
            if start > 0 and end >= start:
                return (start, end)
        except (TypeError, ValueError):
            pass
    return DEFAULT_CALLBACK_PORT_RANGE


def _normalize_headers(raw_headers: Any) -> Dict[str, str]:
    if not isinstance(raw_headers, dict):
        return {}
    resolved: Dict[str, str] = {}
    for key, value in raw_headers.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            resolved[key] = os.path.expandvars(value)
        elif value is not None:
            resolved[key] = str(value)
    return resolved


def get_server_settings(server_name: str) -> Optional[OAuthServerSettings]:
    server_map = load_mcp_server_map()
    server_config = server_map.get(server_name)
    if not isinstance(server_config, dict):
        return None

    oauth_config = server_config.get("oauth")
    if not isinstance(oauth_config, dict) or not oauth_config.get("enabled"):
        return None

    server_url = server_config.get("url")
    server_type = str(server_config.get("type", "")).lower().strip()
    if server_type not in {"http", "sse"}:
        return None
    if not isinstance(server_url, str) or not server_url.strip():
        return None

    redirect_host = str(
        oauth_config.get("redirect_host") or DEFAULT_REDIRECT_HOST
    ).rstrip("/")
    callback_path = str(
        oauth_config.get("callback_path") or DEFAULT_CALLBACK_PATH
    ).strip()
    if not callback_path.startswith("/"):
        callback_path = f"/{callback_path}"

    client_secret = oauth_config.get("client_secret")
    auth_method = oauth_config.get("token_endpoint_auth_method")
    if auth_method is None and client_secret:
        auth_method = "client_secret_post"

    return OAuthServerSettings(
        server_name=server_name,
        server_type=server_type,
        server_url=os.path.expandvars(server_url),
        scope=_normalize_scope(oauth_config),
        client_name=str(oauth_config.get("client_name") or DEFAULT_CLIENT_NAME),
        client_metadata_url=oauth_config.get("client_metadata_url"),
        client_id=oauth_config.get("client_id"),
        client_secret=client_secret,
        token_endpoint_auth_method=auth_method,
        redirect_host=redirect_host,
        callback_path=callback_path,
        callback_port_range=_normalize_port_range(
            oauth_config.get("callback_port_range")
        ),
        callback_timeout=_to_int(
            oauth_config.get("callback_timeout"), DEFAULT_CALLBACK_TIMEOUT
        ),
        auto_authorize_on_autostart=_to_bool(
            oauth_config.get("auto_authorize_on_autostart", True), True
        ),
        manual_callback_only=_to_bool(
            oauth_config.get("manual_callback_only", False), False
        ),
        protocol_version=str(
            oauth_config.get("protocol_version") or DEFAULT_PROTOCOL_VERSION
        ),
        expiry_buffer_seconds=_to_int(
            oauth_config.get("expiry_buffer_seconds"), DEFAULT_EXPIRY_BUFFER_SECONDS
        ),
        base_headers=_normalize_headers(server_config.get("headers")),
    )


def list_oauth_server_names() -> list[str]:
    names: list[str] = []
    for server_name in load_mcp_server_map():
        if get_server_settings(server_name):
            names.append(server_name)
    return sorted(names)
