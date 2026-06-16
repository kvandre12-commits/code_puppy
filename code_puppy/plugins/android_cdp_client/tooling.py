from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import socket
import struct
import time
import urllib.parse
import urllib.request
from typing import Any

from code_puppy.plugins.android_cdp_bridge.tooling import android_cdp_probe

DEFAULT_PORT = 9222
DEFAULT_SOCKET = "chrome_devtools_remote"
DEFAULT_TIMEOUT = 10


class CDPError(RuntimeError):
    """Raised when a CDP operation fails."""


class SimpleWebSocketClient:
    """Minimal WebSocket client for ws:// localhost CDP connections."""

    def __init__(self, ws_url: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.ws_url = ws_url
        self.timeout = timeout
        self.sock: socket.socket | None = None

    def __enter__(self) -> "SimpleWebSocketClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        parsed = urllib.parse.urlparse(self.ws_url)
        if parsed.scheme != "ws":
            raise CDPError("Only ws:// URLs are supported by this client")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        sock = socket.create_connection((host, port), timeout=self.timeout)
        sock.settimeout(self.timeout)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = self._recv_http_response(sock)
        if "101" not in response.splitlines()[0]:
            sock.close()
            raise CDPError(f"WebSocket handshake failed: {response.splitlines()[0]}")

        expected = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
        ).decode("ascii")
        if expected.lower() not in response.lower():
            sock.close()
            raise CDPError("WebSocket handshake response missing expected accept key")

        self.sock = sock

    def _recv_http_response(self, sock: socket.socket) -> str:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8", errors="replace")

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self.sock.close()
        finally:
            self.sock = None

    def send_text(self, text: str) -> None:
        if self.sock is None:
            raise CDPError("WebSocket is not connected")
        payload = text.encode("utf-8")
        self.sock.sendall(self._build_frame(payload, opcode=0x1))

    def recv_text(self) -> str:
        if self.sock is None:
            raise CDPError("WebSocket is not connected")
        opcode, payload = self._read_frame()
        if opcode == 0x8:
            raise CDPError("WebSocket closed by remote peer")
        if opcode != 0x1:
            raise CDPError(f"Unsupported WebSocket opcode: {opcode}")
        return payload.decode("utf-8", errors="replace")

    def _build_frame(self, payload: bytes, opcode: int) -> bytes:
        fin_opcode = 0x80 | (opcode & 0x0F)
        mask_bit = 0x80
        length = len(payload)
        header = bytearray([fin_opcode])
        if length < 126:
            header.append(mask_bit | length)
        elif length < 65536:
            header.append(mask_bit | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(mask_bit | 127)
            header.extend(struct.pack("!Q", length))
        mask_key = os.urandom(4)
        header.extend(mask_key)
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return bytes(header) + masked

    def _read_exact(self, n: int) -> bytes:
        if self.sock is None:
            raise CDPError("WebSocket is not connected")
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise CDPError("Unexpected EOF while reading WebSocket frame")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _read_frame(self) -> tuple[int, bytes]:
        header = self._read_exact(2)
        b1, b2 = header[0], header[1]
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask_key = self._read_exact(4) if masked else b""
        payload = self._read_exact(length) if length else b""
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return opcode, payload



def _http_get_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))



def _ensure_cdp_ready(local_port: int = DEFAULT_PORT) -> dict[str, Any]:
    probe = android_cdp_probe(local_port=local_port, cleanup_forward=False)
    if not probe.get("success"):
        raise CDPError(
            probe.get("error")
            or "CDP probe failed; pair/connect adb first and ensure browser is running"
        )
    return probe



def _list_targets_raw(local_port: int = DEFAULT_PORT) -> list[dict[str, Any]]:
    _ensure_cdp_ready(local_port=local_port)
    data = _http_get_json(f"http://127.0.0.1:{local_port}/json/list")
    if not isinstance(data, list):
        raise CDPError("Unexpected /json/list response")
    return data



def _pick_target(
    targets: list[dict[str, Any]],
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
) -> dict[str, Any]:
    if target_id:
        for target in targets:
            if str(target.get("id")) == target_id:
                return target
        raise CDPError(f"No target found with id={target_id}")

    filtered = [t for t in targets if t.get("type") == "page"]
    if url_contains:
        needle = url_contains.lower()
        filtered = [t for t in filtered if needle in str(t.get("url", "")).lower()]
    if title_contains:
        needle = title_contains.lower()
        filtered = [t for t in filtered if needle in str(t.get("title", "")).lower()]
    if not filtered:
        raise CDPError("No matching page target found")
    return filtered[0]



def _cdp_call(ws_url: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    request_id = random.randint(1000, 999999)
    payload = {"id": request_id, "method": method, "params": params or {}}
    with SimpleWebSocketClient(ws_url) as ws:
        ws.send_text(json.dumps(payload))
        deadline = time.time() + DEFAULT_TIMEOUT
        while time.time() < deadline:
            message = json.loads(ws.recv_text())
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise CDPError(str(message["error"]))
            return message.get("result", {})
    raise CDPError(f"Timed out waiting for CDP response to {method}")



def android_cdp_list_targets(local_port: int = DEFAULT_PORT) -> dict[str, Any]:
    targets = _list_targets_raw(local_port=local_port)
    slim = [
        {
            "id": target.get("id"),
            "type": target.get("type"),
            "title": target.get("title"),
            "url": target.get("url"),
            "webSocketDebuggerUrl": target.get("webSocketDebuggerUrl"),
        }
        for target in targets
    ]
    return {
        "success": True,
        "local_port": local_port,
        "target_count": len(slim),
        "targets": slim,
    }



def android_cdp_get_page_info(
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    targets = _list_targets_raw(local_port=local_port)
    target = _pick_target(
        targets,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
    )
    ws_url = str(target.get("webSocketDebuggerUrl") or "")
    if not ws_url:
        raise CDPError("Target does not expose webSocketDebuggerUrl")

    _cdp_call(ws_url, "Runtime.enable")
    eval_result = _cdp_call(
        ws_url,
        "Runtime.evaluate",
        {
            "expression": "JSON.stringify({title: document.title, url: location.href, htmlLength: document.documentElement.outerHTML.length, readyState: document.readyState})",
            "returnByValue": True,
            "awaitPromise": False,
        },
    )
    value = (((eval_result.get("result") or {}).get("value")) or "{}")
    parsed_value = json.loads(value) if isinstance(value, str) else value
    return {
        "success": True,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "page_info": parsed_value,
    }



def android_cdp_navigate(
    url: str,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be a valid http/https URL")

    targets = _list_targets_raw(local_port=local_port)
    target = _pick_target(
        targets,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
    )
    ws_url = str(target.get("webSocketDebuggerUrl") or "")
    if not ws_url:
        raise CDPError("Target does not expose webSocketDebuggerUrl")

    _cdp_call(ws_url, "Page.enable")
    result = _cdp_call(ws_url, "Page.navigate", {"url": url})
    time.sleep(1.0)
    info = android_cdp_get_page_info(target_id=str(target.get("id")), local_port=local_port)
    return {
        "success": True,
        "frameId": result.get("frameId"),
        "loaderId": result.get("loaderId"),
        "target": info.get("target"),
        "page_info": info.get("page_info"),
    }



def android_cdp_eval_js(
    expression: str,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    return_by_value: bool = True,
) -> dict[str, Any]:
    if not expression.strip():
        raise ValueError("expression is required")

    targets = _list_targets_raw(local_port=local_port)
    target = _pick_target(
        targets,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
    )
    ws_url = str(target.get("webSocketDebuggerUrl") or "")
    if not ws_url:
        raise CDPError("Target does not expose webSocketDebuggerUrl")

    _cdp_call(ws_url, "Runtime.enable")
    result = _cdp_call(
        ws_url,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True,
        },
    )
    remote = result.get("result", {})
    exception = result.get("exceptionDetails")
    return {
        "success": exception is None,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "result": remote,
        "exceptionDetails": exception,
    }
