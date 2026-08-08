#!/usr/bin/env python3
"""Send signed requests to the private operator channel."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from code_puppy.plugins.private_operator_channel.runtime import build_signed_request


def _load_args_object(args_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(args_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"args_json must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("args_json must decode to a JSON object")
    return payload


def _resolve_secret(shared_secret: str, secret_env: str) -> str:
    secret = shared_secret or os.environ.get(secret_env, "")
    if not secret:
        raise ValueError(
            f"Missing shared secret. Pass --shared-secret or set {secret_env}."
        )
    return secret


def _build_ssl_context(
    *,
    ca_file: str = "",
    client_cert: str = "",
    client_key: str = "",
    insecure_skip_verify: bool = False,
) -> ssl.SSLContext | None:
    if not any([ca_file.strip(), client_cert.strip(), client_key.strip(), insecure_skip_verify]):
        return None
    if insecure_skip_verify:
        context = ssl._create_unverified_context()  # noqa: SLF001
    else:
        context = ssl.create_default_context(cafile=ca_file.strip() or None)
    if client_cert.strip():
        context.load_cert_chain(
            certfile=str(Path(client_cert).expanduser().resolve()),
            keyfile=str(Path(client_key or client_cert).expanduser().resolve()),
        )
    return context


def build_request_payload(
    *,
    action: str,
    args_json: str,
    shared_secret: str,
) -> dict[str, Any]:
    args = _load_args_object(args_json)
    return build_signed_request(action=action, args=args, shared_secret=shared_secret)


def send_request(
    *,
    url: str,
    payload: dict[str, Any],
    timeout: float,
    ssl_context: ssl.SSLContext | None,
) -> dict[str, Any]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout, context=ssl_context) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("server response must be a JSON object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8766/v1/control")
    parser.add_argument("--action", required=True)
    parser.add_argument("--args-json", default="{}")
    parser.add_argument("--shared-secret", default="")
    parser.add_argument("--secret-env", default="PRIVATE_OPERATOR_CHANNEL_SECRET")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--ca-file", default="")
    parser.add_argument("--client-cert", default="")
    parser.add_argument("--client-key", default="")
    parser.add_argument("--insecure-skip-verify", action="store_true")
    parser.add_argument("--show-request", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        secret = _resolve_secret(args.shared_secret, args.secret_env)
        payload = build_request_payload(
            action=args.action,
            args_json=args.args_json,
            shared_secret=secret,
        )
        if args.show_request:
            print(json.dumps(payload, indent=2))
        ssl_context = _build_ssl_context(
            ca_file=args.ca_file,
            client_cert=args.client_cert,
            client_key=args.client_key,
            insecure_skip_verify=args.insecure_skip_verify,
        )
        response = send_request(
            url=args.url,
            payload=payload,
            timeout=args.timeout,
            ssl_context=ssl_context,
        )
    except Exception as exc:  # pragma: no cover - CLI safety seam
        print(json.dumps({"success": False, "error": str(exc)}), file=sys.stderr)
        return 1

    rendered = json.dumps(response, indent=2, sort_keys=True)
    if args.output.strip():
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(str(output_path))
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
