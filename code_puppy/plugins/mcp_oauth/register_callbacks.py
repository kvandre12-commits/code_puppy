"""Plugin callbacks for generic OAuth-backed MCP servers."""

from __future__ import annotations

import asyncio
import copy
import datetime as dt
from typing import Any, List, Optional, Tuple

from code_puppy.callbacks import register_callback
from code_puppy.messaging import emit_error, emit_info, emit_success, emit_warning
from code_puppy.mcp_ import ServerConfig, get_mcp_manager

from .config import get_server_settings, list_oauth_server_names
from .oauth_flow import ensure_access_token
from .storage import clear_token_state, get_token_expiry, load_token_state

COMMAND_AUTH = "mcp-oauth-auth"
COMMAND_STATUS = "mcp-oauth-status"
COMMAND_LOGOUT = "mcp-oauth-logout"


def _custom_help() -> List[Tuple[str, str]]:
    return [
        (COMMAND_AUTH, "Authenticate an OAuth-backed MCP server"),
        (COMMAND_STATUS, "Show OAuth status for MCP servers"),
        (COMMAND_LOGOUT, "Forget stored OAuth tokens for an MCP server"),
    ]


def _parse_server_name(command: str) -> Optional[str]:
    parts = command.split(maxsplit=1)
    if len(parts) < 2:
        return None
    server_name = parts[1].strip()
    return server_name or None


def _managed_server_is_running(managed: Any) -> bool:
    status_getter = getattr(managed, "get_status", None)
    if callable(status_getter):
        try:
            status = status_getter()
        except Exception:
            status = None
        if isinstance(status, dict) and (
            status.get("server_available") or status.get("state") == "running"
        ):
            return True

    pydantic_server = getattr(managed, "_pydantic_server", None)
    return bool(getattr(pydantic_server, "is_running", False))


async def _apply_runtime_bearer(server_name: str, access_token: str) -> bool:
    settings = get_server_settings(server_name)
    if not settings:
        return False

    manager = get_mcp_manager()
    registry_config = manager.get_server_by_name(server_name)
    if not registry_config:
        emit_warning(f"MCP server '{server_name}' is not registered.")
        return False

    managed = manager.get_server(registry_config.id)
    if managed is None:
        emit_warning(f"MCP server '{server_name}' has no managed instance.")
        return False
    if _managed_server_is_running(managed):
        emit_warning(
            f"MCP server '{server_name}' is already running. Restart it before applying new OAuth credentials."
        )
        return False

    runtime_config = ServerConfig(
        id=registry_config.id,
        name=registry_config.name,
        type=registry_config.type,
        enabled=registry_config.enabled,
        config=copy.deepcopy(registry_config.config),
    )
    headers = dict(runtime_config.config.get("headers") or {})
    headers["Authorization"] = f"Bearer {access_token}"
    runtime_config.config["headers"] = headers

    managed.config = runtime_config
    managed._pydantic_server = None
    managed._create_server()
    return True


def _restore_registry_backed_config(server_name: str) -> None:
    manager = get_mcp_manager()
    registry_config = manager.get_server_by_name(server_name)
    if not registry_config:
        return
    managed = manager.get_server(registry_config.id)
    if managed is None:
        return
    if _managed_server_is_running(managed):
        emit_warning(
            f"MCP server '{server_name}' is still running. Restart it to drop cached OAuth headers."
        )
        return
    managed.config = ServerConfig(
        id=registry_config.id,
        name=registry_config.name,
        type=registry_config.type,
        enabled=registry_config.enabled,
        config=copy.deepcopy(registry_config.config),
    )
    managed._pydantic_server = None
    managed._create_server()


def _format_expiry(expires_at: Optional[float]) -> str:
    if expires_at is None:
        return "unknown"
    ts = dt.datetime.fromtimestamp(expires_at, tz=dt.timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")


def _show_status(server_name: Optional[str] = None) -> None:
    names = [server_name] if server_name else list_oauth_server_names()
    if not names:
        emit_info("No OAuth-enabled MCP servers are configured.")
        return

    for name in names:
        settings = get_server_settings(name)
        if not settings:
            emit_warning(f"'{name}' is not configured for MCP OAuth.")
            continue
        state = load_token_state(name)
        token_payload = (
            state.get("tokens") if isinstance(state.get("tokens"), dict) else {}
        )
        client_info = (
            state.get("client_info")
            if isinstance(state.get("client_info"), dict)
            else {}
        )
        has_access = bool(token_payload.get("access_token"))
        has_refresh = bool(token_payload.get("refresh_token"))
        emit_info(f" {name}")
        emit_info(f"  url: {settings.server_url}")
        emit_info(f"  access token: {'yes' if has_access else 'no'}")
        emit_info(f"  refresh token: {'yes' if has_refresh else 'no'}")
        emit_info(f"  expires at: {_format_expiry(get_token_expiry(name))}")
        emit_info(
            f"  client id: {client_info.get('client_id', settings.client_id or 'dynamic / unknown')}"
        )
        emit_info(
            f"  auto authorize on autostart: {'yes' if settings.auto_authorize_on_autostart else 'no'}"
        )


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive
            error["value"] = exc

    import threading

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "value" in error:
        raise error["value"]
    return result.get("value")


def _handle_auth(server_name: str, force_reauth: bool = False) -> bool:
    settings = get_server_settings(server_name)
    if not settings:
        emit_error(f"'{server_name}' is not an OAuth-enabled MCP server.")
        return True
    access_token = _run_async(
        ensure_access_token(
            settings,
            allow_interactive=True,
            force_reauth=force_reauth,
        )
    )
    if not access_token:
        return True
    if _run_async(_apply_runtime_bearer(server_name, access_token)):
        emit_success(f"Bearer token injected for '{server_name}'.")
    else:
        emit_info(
            f"OAuth is ready for '{server_name}', but the MCP server may need a restart before the new token is used."
        )
    return True


def _handle_logout(server_name: str) -> bool:
    settings = get_server_settings(server_name)
    if not settings:
        emit_error(f"'{server_name}' is not an OAuth-enabled MCP server.")
        return True
    clear_token_state(server_name, keep_client_info=True)
    _restore_registry_backed_config(server_name)
    emit_success(f"Stored OAuth tokens cleared for '{server_name}'.")
    emit_info("If that server is currently running, restart it before reusing it.")
    return True


def _handle_custom_command(command: str, name: str) -> Optional[object]:
    if name == COMMAND_AUTH:
        server_name = _parse_server_name(command)
        if not server_name:
            emit_info(f"Usage: /{COMMAND_AUTH} <server-name>")
            emit_info(
                f"Configured OAuth MCP servers: {', '.join(list_oauth_server_names()) or '(none)'}"
            )
            return True
        return _handle_auth(server_name)

    if name == COMMAND_STATUS:
        _show_status(_parse_server_name(command))
        return True

    if name == COMMAND_LOGOUT:
        server_name = _parse_server_name(command)
        if not server_name:
            emit_info(f"Usage: /{COMMAND_LOGOUT} <server-name>")
            return True
        return _handle_logout(server_name)

    return None


async def _pre_mcp_autostart(agent_name: str, server_names: List[str]) -> None:
    del agent_name
    for server_name in server_names:
        settings = get_server_settings(server_name)
        if not settings:
            continue
        access_token = await ensure_access_token(
            settings,
            allow_interactive=settings.auto_authorize_on_autostart,
            force_reauth=False,
        )
        if not access_token:
            emit_warning(
                f"Skipping bearer injection for '{server_name}' because OAuth is not ready."
            )
            continue
        ok = await _apply_runtime_bearer(server_name, access_token)
        if ok:
            emit_info(f"OAuth header prepared for MCP server '{server_name}'.")


register_callback("custom_command_help", _custom_help)
register_callback("custom_command", _handle_custom_command)
register_callback("pre_mcp_autostart", _pre_mcp_autostart)
