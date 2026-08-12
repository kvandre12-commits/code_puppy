from __future__ import annotations

import argparse
import json
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import (
    PrivateOperatorChannelConfig,
    load_private_operator_channel_config,
)
from .runtime import PrivateOperatorChannelRuntime


def _resolve_tls_path(raw: str, label: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError(f"{label} is required when TLS is enabled")
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    return str(path)


def build_ssl_context(config: PrivateOperatorChannelConfig) -> ssl.SSLContext | None:
    if not config.tls_enabled:
        return None
    certfile = _resolve_tls_path(config.tls_certfile, "tls_certfile")
    keyfile = _resolve_tls_path(config.tls_keyfile, "tls_keyfile")
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    if config.tls_client_cafile.strip():
        cafile = _resolve_tls_path(config.tls_client_cafile, "tls_client_cafile")
        context.load_verify_locations(cafile=cafile)
        context.verify_mode = ssl.CERT_OPTIONAL
    if config.require_client_certificate:
        if not config.tls_client_cafile.strip():
            raise ValueError(
                "tls_client_cafile is required when require_client_certificate is true"
            )
        context.verify_mode = ssl.CERT_REQUIRED
    return context


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def make_handler(runtime: PrivateOperatorChannelRuntime):
    class PrivateOperatorRequestHandler(BaseHTTPRequestHandler):
        server_version = "PrivateOperatorChannel/0.1"

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self._write_json(404, {"success": False, "error": "not_found"})
                return
            self._write_json(
                200,
                {
                    "success": True,
                    "summary": (
                        f"private operator channel listening on "
                        f"{runtime.config.bind_host}:{runtime.config.port}"
                    ),
                    "tls_enabled": runtime.config.tls_enabled,
                    "require_client_certificate": runtime.config.require_client_certificate,
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/control":
                self._write_json(404, {"success": False, "error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                self._write_json(
                    400, {"success": False, "error": "invalid_content_length"}
                )
                return
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except json.JSONDecodeError:
                self._write_json(400, {"success": False, "error": "invalid_json"})
                return
            if not isinstance(payload, dict):
                self._write_json(
                    400, {"success": False, "error": "payload_must_be_object"}
                )
                return
            status_code, result = runtime.handle_payload(payload)
            self._write_json(status_code, result)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            del format, args

        def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
            body = _json_bytes(payload)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return PrivateOperatorRequestHandler


def build_http_server(
    *,
    config: PrivateOperatorChannelConfig,
    runtime: PrivateOperatorChannelRuntime,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((config.bind_host, config.port), make_handler(runtime))
    ssl_context = build_ssl_context(config)
    if ssl_context is not None:
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    return server


def serve(
    *,
    config_path: str = "",
    bind_host: str = "",
    port: int = 0,
) -> dict[str, Any]:
    config, resolved_path, config_exists = load_private_operator_channel_config(
        config_path
    )
    overrides: dict[str, Any] = {}
    if bind_host.strip():
        overrides["bind_host"] = bind_host.strip()
    if port > 0:
        overrides["port"] = port
    if overrides:
        config = config.with_overrides(**overrides)
    runtime = PrivateOperatorChannelRuntime(
        config=config,
        config_path=resolved_path,
        config_exists=config_exists,
    )
    server = build_http_server(config=config, runtime=runtime)
    bound_host, bound_port = server.server_address[:2]
    scheme = "https" if config.tls_enabled else "http"
    try:
        print(
            f"private operator channel listening on {scheme}://{bound_host}:{bound_port} "
            f"using config {resolved_path}"
        )
        server.serve_forever()
    finally:
        server.server_close()
    return {
        "success": True,
        "bind_host": str(bound_host),
        "port": int(bound_port),
        "config_path": str(resolved_path),
        "tls_enabled": config.tls_enabled,
        "require_client_certificate": config.require_client_certificate,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the private operator channel server."
    )
    parser.add_argument("--config", default="", help="Optional JSON config path.")
    parser.add_argument("--bind-host", default="", help="Override bind host.")
    parser.add_argument("--port", type=int, default=0, help="Override bind port.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    serve(config_path=args.config, bind_host=args.bind_host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
