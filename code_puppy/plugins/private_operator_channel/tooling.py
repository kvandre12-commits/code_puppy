from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import load_private_operator_channel_config, write_example_config
from .runtime import (
    _capability_for_android_target,
    build_signed_request,
    build_status_snapshot,
)

_TOOL_STATUS = "private_operator_channel_status"
_TOOL_WRITE_CONFIG = "private_operator_channel_write_example_config"
_TOOL_SIGN_REQUEST = "private_operator_channel_sign_request"


def private_operator_channel_status(
    config_path: str = "",
    include_authority: bool = True,
    include_bus: bool = True,
) -> dict[str, Any]:
    config, resolved_path, config_exists = load_private_operator_channel_config(
        config_path
    )
    return build_status_snapshot(
        config,
        config_path=resolved_path,
        config_exists=config_exists,
        include_authority=include_authority,
        include_bus=include_bus,
    )


def private_operator_channel_write_example_config(
    output_path: str = "",
    overwrite: bool = False,
) -> dict[str, Any]:
    return write_example_config(output_path=output_path, overwrite=overwrite)


def private_operator_channel_sign_request(
    action: str,
    args_json: str = "{}",
    shared_secret: str = "",
    secret_env: str = "PRIVATE_OPERATOR_CHANNEL_SECRET",
    output_path: str = "",
) -> dict[str, Any]:
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"invalid args_json: {exc}"}
    if not isinstance(args, dict):
        return {"success": False, "error": "args_json must decode to an object"}
    secret = shared_secret or os.environ.get(secret_env, "")
    if not secret:
        return {
            "success": False,
            "error": "missing_shared_secret",
            "hint": f"Pass shared_secret or set {secret_env}.",
        }
    payload = build_signed_request(action=action, args=args, shared_secret=secret)
    result: dict[str, Any] = {"success": True, "payload": payload}
    if action == "android_open":
        target = str(args.get("target", "") or "").strip()
        if target:
            result["required_capability"] = _capability_for_android_target(target)
    if output_path.strip():
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        result["output_path"] = str(path)
        return result
    return result


def custom_help() -> list[tuple[str, str]]:
    return [("private-channel", "Show private operator channel status")]


def handle_custom_command(command: str, name: str) -> bool | None:
    del command
    if name != "private-channel":
        return None
    status = private_operator_channel_status()
    print(status.get("summary", "private operator channel status unavailable"))
    print(f"config: {status.get('config_path')}")
    print(f"actions: {', '.join(status.get('allowed_actions', []))}")
    return True


def advertise_tools(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_TOOL_STATUS, _TOOL_WRITE_CONFIG, _TOOL_SIGN_REQUEST]
