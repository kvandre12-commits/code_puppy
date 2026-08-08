from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = "~/.code_puppy/private_operator_channel.json"
DEFAULT_AUDIT_LOG_PATH = "outputs/private_operator_channel_audit.jsonl"
DEFAULT_SHARED_SECRET_ENV = "PRIVATE_OPERATOR_CHANNEL_SECRET"
READ_ONLY_ACTIONS = (
    "ping",
    "status",
    "authority_status",
    "bus_status",
    "tail_bus",
)
EFFECTFUL_ACTIONS = ("android_open",)
DEFAULT_ALLOWED_ACTIONS = READ_ONLY_ACTIONS + EFFECTFUL_ACTIONS
DEFAULT_ALLOWED_ANDROID_TARGETS = (
    "wifi",
    "bluetooth",
    "app_settings",
    "notification_settings",
    "developer options",
    "brave",
)


@dataclass(frozen=True)
class PrivateOperatorChannelConfig:
    bind_host: str = "127.0.0.1"
    port: int = 8766
    shared_secret_env: str = DEFAULT_SHARED_SECRET_ENV
    max_skew_seconds: int = 90
    allow_effectful_actions: bool = False
    allowed_actions: tuple[str, ...] = DEFAULT_ALLOWED_ACTIONS
    allowed_android_targets: tuple[str, ...] = DEFAULT_ALLOWED_ANDROID_TARGETS
    audit_log_path: str = DEFAULT_AUDIT_LOG_PATH
    tls_enabled: bool = False
    tls_certfile: str = ""
    tls_keyfile: str = ""
    tls_client_cafile: str = ""
    require_client_certificate: bool = False

    def with_overrides(self, **overrides: Any) -> "PrivateOperatorChannelConfig":
        data = asdict(self)
        data.update({key: value for key, value in overrides.items() if value is not None})
        if isinstance(data.get("allowed_actions"), list):
            data["allowed_actions"] = tuple(str(item) for item in data["allowed_actions"])
        if isinstance(data.get("allowed_android_targets"), list):
            data["allowed_android_targets"] = tuple(
                str(item) for item in data["allowed_android_targets"]
            )
        return PrivateOperatorChannelConfig(**data)

    @property
    def effectful_actions(self) -> tuple[str, ...]:
        return tuple(action for action in self.allowed_actions if action in EFFECTFUL_ACTIONS)


def resolve_config_path(config_path: str = "") -> Path:
    raw = config_path.strip() or DEFAULT_CONFIG_PATH
    return Path(raw).expanduser().resolve()


def resolve_audit_log_path(config: PrivateOperatorChannelConfig) -> Path:
    return Path(config.audit_log_path).expanduser().resolve()


def _normalize_loaded_mapping(raw: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in (
        "bind_host",
        "port",
        "shared_secret_env",
        "max_skew_seconds",
        "allow_effectful_actions",
        "audit_log_path",
        "tls_enabled",
        "tls_certfile",
        "tls_keyfile",
        "tls_client_cafile",
        "require_client_certificate",
    ):
        if key in raw:
            normalized[key] = raw[key]
    if "allowed_actions" in raw and isinstance(raw["allowed_actions"], list):
        normalized["allowed_actions"] = tuple(str(item) for item in raw["allowed_actions"])
    if "allowed_android_targets" in raw and isinstance(raw["allowed_android_targets"], list):
        normalized["allowed_android_targets"] = tuple(
            str(item) for item in raw["allowed_android_targets"]
        )
    return normalized


def load_private_operator_channel_config(
    config_path: str = "",
) -> tuple[PrivateOperatorChannelConfig, Path, bool]:
    path = resolve_config_path(config_path)
    if not path.exists():
        return PrivateOperatorChannelConfig(), path, False
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("private operator channel config must be a JSON object")
    normalized = _normalize_loaded_mapping(raw)
    return PrivateOperatorChannelConfig().with_overrides(**normalized), path, True


def example_config_dict() -> dict[str, Any]:
    return {
        "bind_host": "127.0.0.1",
        "port": 8766,
        "shared_secret_env": DEFAULT_SHARED_SECRET_ENV,
        "max_skew_seconds": 90,
        "allow_effectful_actions": False,
        "allowed_actions": list(DEFAULT_ALLOWED_ACTIONS),
        "allowed_android_targets": list(DEFAULT_ALLOWED_ANDROID_TARGETS),
        "audit_log_path": DEFAULT_AUDIT_LOG_PATH,
        "tls_enabled": False,
        "tls_certfile": "",
        "tls_keyfile": "",
        "tls_client_cafile": "",
        "require_client_certificate": False,
    }


def write_example_config(output_path: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = resolve_config_path(output_path)
    if path.exists() and not overwrite:
        return {
            "success": False,
            "path": str(path),
            "reason": "file_exists",
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(example_config_dict(), indent=2) + "\n", encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "overwrite": overwrite,
        "summary": (
            "Example config written. Set the shared secret via the configured env var, "
            "bind only to localhost or a private overlay IP, and optionally attach TLS/client-cert files."
        ),
    }


def config_snapshot(
    config: PrivateOperatorChannelConfig,
    *,
    config_path: Path,
    config_exists: bool,
    secret_present: bool,
) -> dict[str, Any]:
    return {
        "config_path": str(config_path),
        "config_exists": config_exists,
        "bind_host": config.bind_host,
        "port": config.port,
        "shared_secret_env": config.shared_secret_env,
        "secret_present": secret_present,
        "max_skew_seconds": config.max_skew_seconds,
        "allow_effectful_actions": config.allow_effectful_actions,
        "allowed_actions": list(config.allowed_actions),
        "allowed_android_targets": list(config.allowed_android_targets),
        "audit_log_path": str(resolve_audit_log_path(config)),
        "tls_enabled": config.tls_enabled,
        "tls_certfile": config.tls_certfile,
        "tls_keyfile_configured": bool(config.tls_keyfile),
        "tls_client_cafile": config.tls_client_cafile,
        "require_client_certificate": config.require_client_certificate,
    }
