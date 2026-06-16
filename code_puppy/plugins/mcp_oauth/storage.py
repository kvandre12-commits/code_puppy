"""Token storage for the MCP OAuth plugin."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from mcp.client.auth import TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from .config import get_token_storage_path


_DIR_MODE = 0o700
_FILE_MODE = 0o600


def _chmod_best_effort(path: str, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


class ServerTokenStorage(TokenStorage):
    """File-backed token storage for one MCP server."""

    def __init__(self, server_name: str, expiry_buffer_seconds: int = 60):
        self.server_name = server_name
        self.expiry_buffer_seconds = max(0, int(expiry_buffer_seconds))
        self.path = get_token_storage_path(server_name)

    def load_state(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _chmod_best_effort(str(self.path.parent), _DIR_MODE)
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        _chmod_best_effort(str(self.path), _FILE_MODE)

    def clear(self, keep_client_info: bool = True) -> None:
        state = self.load_state() if keep_client_info else {}
        state.pop("tokens", None)
        if keep_client_info:
            self.save_state(state)
        elif self.path.exists():
            self.path.unlink()

    async def get_tokens(self) -> OAuthToken | None:
        state = self.load_state()
        token_payload = state.get("tokens")
        if not isinstance(token_payload, dict):
            return None

        payload = dict(token_payload)
        expires_at = payload.pop("expires_at", None)
        if expires_at is not None:
            try:
                expires_at_value = float(expires_at)
            except (TypeError, ValueError):
                expires_at_value = None
            else:
                if expires_at_value <= time.time() + self.expiry_buffer_seconds:
                    payload["access_token"] = ""
                    payload["expires_in"] = 0

        try:
            return OAuthToken.model_validate(payload)
        except Exception:
            return None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        state = self.load_state()
        payload = tokens.model_dump(mode="json", exclude_none=True)
        expires_in = payload.get("expires_in")
        if expires_in is not None:
            try:
                payload["expires_at"] = time.time() + float(expires_in)
            except (TypeError, ValueError):
                pass
        payload["updated_at"] = time.time()
        state["tokens"] = payload
        self.save_state(state)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        state = self.load_state()
        client_info = state.get("client_info")
        if not isinstance(client_info, dict):
            return None
        try:
            return OAuthClientInformationFull.model_validate(client_info)
        except Exception:
            return None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        state = self.load_state()
        state["client_info"] = client_info.model_dump(mode="json", exclude_none=True)
        self.save_state(state)


def load_token_state(server_name: str) -> Dict[str, Any]:
    return ServerTokenStorage(server_name).load_state()


def clear_token_state(server_name: str, keep_client_info: bool = True) -> None:
    ServerTokenStorage(server_name).clear(keep_client_info=keep_client_info)


def get_stored_access_token(server_name: str) -> Optional[str]:
    state = load_token_state(server_name)
    tokens = state.get("tokens")
    if not isinstance(tokens, dict):
        return None
    access_token = tokens.get("access_token")
    return access_token if isinstance(access_token, str) and access_token else None


def has_stored_refresh_token(server_name: str) -> bool:
    state = load_token_state(server_name)
    tokens = state.get("tokens")
    if not isinstance(tokens, dict):
        return False
    refresh_token = tokens.get("refresh_token")
    return bool(isinstance(refresh_token, str) and refresh_token)


def get_token_expiry(server_name: str) -> Optional[float]:
    state = load_token_state(server_name)
    tokens = state.get("tokens")
    if not isinstance(tokens, dict):
        return None
    expires_at = tokens.get("expires_at")
    try:
        return float(expires_at) if expires_at is not None else None
    except (TypeError, ValueError):
        return None
