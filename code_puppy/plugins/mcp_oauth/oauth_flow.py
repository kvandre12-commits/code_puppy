"""OAuth flow helpers for HTTP/SSE MCP servers."""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata

from code_puppy.messaging import emit_error, emit_info, emit_success, emit_warning

from ..oauth_puppy_html import oauth_failure_html, oauth_success_html
from .config import OAuthServerSettings
from .storage import (
    ServerTokenStorage,
    get_stored_access_token,
    has_stored_refresh_token,
)

logger = logging.getLogger(__name__)


@dataclass
class CallbackResult:
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None


class _CallbackHandler(BaseHTTPRequestHandler):
    server: "OAuthCallbackServer"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != self.server.callback_path:
            self._write_response(
                404,
                oauth_failure_html("MCP OAuth", "Wrong callback path. OAuth gremlins win."),
            )
            return

        params = parse_qs(parsed.query)
        self.server.result.code = params.get("code", [None])[0]
        self.server.result.state = params.get("state", [None])[0]
        self.server.result.error = params.get("error", [None])[0]

        if self.server.result.code:
            self._write_response(
                200,
                oauth_success_html(
                    "MCP OAuth",
                    "Auth captured. You can close this tab and go back to Code Puppy.",
                ),
            )
        else:
            reason = self.server.result.error or "Missing authorization code"
            self._write_response(400, oauth_failure_html("MCP OAuth", reason))

        self.server.received_event.set()
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, log_format: str, *args: Any) -> None:
        return

    def _write_response(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class OAuthCallbackServer(HTTPServer):
    def __init__(self, host: str, port: int, callback_path: str) -> None:
        super().__init__((host, port), _CallbackHandler, bind_and_activate=True)
        self.callback_path = callback_path
        self.result = CallbackResult()
        self.received_event = threading.Event()


class BrowserOAuthSession:
    """Owns redirect URI + callback capture for one OAuth run."""

    def __init__(self, settings: OAuthServerSettings):
        self.settings = settings
        self.port = self._choose_port()
        self.redirect_uri = self._build_redirect_uri(self.port)

    def _choose_port(self) -> int:
        for port in range(
            self.settings.callback_port_range[0],
            self.settings.callback_port_range[1] + 1,
        ):
            try:
                probe = OAuthCallbackServer(
                    self.settings.callback_bind_host,
                    port,
                    self.settings.callback_path,
                )
            except OSError:
                continue
            probe.server_close()
            return port
        return self.settings.callback_port_range[0]

    def _build_redirect_uri(self, port: int) -> str:
        return (
            f"{self.settings.redirect_host}:{port}"
            f"{self.settings.callback_path}"
        )

    async def redirect_handler(self, authorization_url: str) -> None:
        emit_info(
            f"OAuth needed for MCP server '{self.settings.server_name}'."
        )
        emit_info(f"Open this URL if your browser does not launch automatically:\n{authorization_url}")
        try:
            import webbrowser

            from code_puppy.tools.common import should_suppress_browser

            if should_suppress_browser():
                emit_info("[HEADLESS MODE] Browser launch suppressed.")
                return
            await asyncio.to_thread(webbrowser.open, authorization_url)
        except Exception as exc:  # pragma: no cover - browser opening is fickle
            emit_warning(f"Could not open browser automatically: {exc}")

    async def callback_handler(self) -> tuple[str, str | None]:
        if not self.settings.manual_callback_only:
            result = await self._wait_for_local_callback()
            if result:
                return result
        return await self._prompt_for_manual_callback()

    async def _wait_for_local_callback(self) -> Optional[Tuple[str, Optional[str]]]:
        try:
            server = OAuthCallbackServer(
                self.settings.callback_bind_host,
                self.port,
                self.settings.callback_path,
            )
        except OSError:
            emit_warning(
                "The selected callback port is busy now. Falling back to manual code paste."
            )
            return None

        def run_server() -> None:
            with server:
                server.serve_forever()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        emit_info(f"Listening for OAuth callback on {self.redirect_uri}")

        try:
            received = await asyncio.to_thread(
                server.received_event.wait,
                self.settings.callback_timeout,
            )
        finally:
            try:
                server.shutdown()
            except Exception:
                pass
            thread.join(timeout=2)

        if not received:
            emit_warning("OAuth callback timed out. Falling back to manual paste.")
            return None
        if server.result.error:
            emit_error(f"OAuth callback error: {server.result.error}")
            return None
        if not server.result.code:
            emit_error("OAuth callback arrived but no auth code was present.")
            return None
        emit_success("OAuth callback received.")
        return server.result.code, server.result.state

    async def _prompt_for_manual_callback(self) -> tuple[str, str | None]:
        emit_info(
            "If the browser lands on a broken localhost page, that's fine — copy the full callback URL."
        )
        prompt = (
            "Paste the full callback URL, or '<code> <state>' if you extracted them manually: "
        )
        raw = await asyncio.to_thread(input, prompt)
        code, state = parse_callback_input(raw)
        if not code:
            raise RuntimeError("No authorization code was provided")
        return code, state


def parse_callback_input(raw_input: str) -> tuple[Optional[str], Optional[str]]:
    value = raw_input.strip()
    if not value:
        return None, None

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        params = parse_qs(parsed.query)
        return params.get("code", [None])[0], params.get("state", [None])[0]

    if "#" in value:
        code, state = value.split("#", 1)
        return code.strip() or None, state.strip() or None

    parts = value.split()
    if len(parts) >= 2:
        return parts[0].strip() or None, parts[1].strip() or None
    return value, None


async def _seed_client_info(
    settings: OAuthServerSettings,
    storage: ServerTokenStorage,
    redirect_uri: str,
) -> None:
    if not settings.client_id:
        return
    existing = await storage.get_client_info()
    if existing and existing.client_id == settings.client_id:
        return

    auth_method = settings.token_endpoint_auth_method or "none"
    client_info = OAuthClientInformationFull(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        token_endpoint_auth_method=auth_method,
        redirect_uris=[redirect_uri],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=settings.scope,
        client_name=settings.client_name,
    )
    await storage.set_client_info(client_info)


async def ensure_access_token(
    settings: OAuthServerSettings,
    *,
    allow_interactive: bool = True,
    force_reauth: bool = False,
) -> Optional[str]:
    """Ensure a valid access token exists for the given MCP server."""

    storage = ServerTokenStorage(
        settings.server_name,
        expiry_buffer_seconds=settings.expiry_buffer_seconds,
    )
    if force_reauth:
        storage.clear(keep_client_info=True)

    if (
        not allow_interactive
        and not get_stored_access_token(settings.server_name)
        and not has_stored_refresh_token(settings.server_name)
    ):
        emit_warning(
            f"MCP OAuth for '{settings.server_name}' needs initial login. "
            "Run /mcp-oauth-auth first or enable auto_authorize_on_autostart."
        )
        return None

    browser_session = BrowserOAuthSession(settings)
    await _seed_client_info(settings, storage, browser_session.redirect_uri)

    client_metadata = OAuthClientMetadata(
        redirect_uris=[browser_session.redirect_uri],
        token_endpoint_auth_method=settings.token_endpoint_auth_method,
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=settings.scope,
        client_name=settings.client_name,
    )

    provider = OAuthClientProvider(
        server_url=settings.server_url,
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=browser_session.redirect_handler if allow_interactive else None,
        callback_handler=browser_session.callback_handler if allow_interactive else None,
        timeout=float(settings.callback_timeout),
        client_metadata_url=settings.client_metadata_url,
    )

    headers = dict(settings.base_headers)
    headers.pop("Authorization", None)
    headers.update(
        {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": settings.protocol_version,
        }
    )
    probe_body = {
        "jsonrpc": "2.0",
        "id": "code-puppy-mcp-oauth-probe",
        "method": "initialize",
        "params": {
            "protocolVersion": settings.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "code-puppy-mcp-oauth", "version": "0.1.0"},
        },
    }

    try:
        async with httpx.AsyncClient(
            auth=provider,
            headers=headers,
            timeout=httpx.Timeout(20.0, connect=10.0, read=15.0),
            follow_redirects=False,
        ) as client:
            response = await client.post(settings.server_url, json=probe_body)
            await response.aread()
    except Exception as exc:
        logger.debug("OAuth probe request ended with exception: %s", exc)

    access_token = get_stored_access_token(settings.server_name)
    if access_token:
        emit_success(f"OAuth ready for MCP server '{settings.server_name}'.")
        return access_token

    emit_error(
        f"OAuth did not yield an access token for MCP server '{settings.server_name}'."
    )
    return None
