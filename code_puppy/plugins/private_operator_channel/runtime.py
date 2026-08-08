from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from code_puppy.plugins.android_friendly_router.tooling import android_open
from code_puppy.plugins.authority_gateway.tooling import authority_gateway_status
from code_puppy.plugins.project_os_supervisor.tooling import project_os_bus_status, project_os_tail

from .config import PrivateOperatorChannelConfig, config_snapshot, resolve_audit_log_path

_AUTH_FAILURE_CODES = {"invalid_signature", "missing_secret", "stale_timestamp", "replayed_nonce"}


@dataclass
class NonceCache:
    ttl_seconds: int
    _entries: dict[str, float] = field(default_factory=dict)

    def accept(self, nonce: str, now: float | None = None) -> bool:
        moment = now if now is not None else time.time()
        expired = [key for key, expiry in self._entries.items() if expiry <= moment]
        for key in expired:
            self._entries.pop(key, None)
        if nonce in self._entries:
            return False
        self._entries[nonce] = moment + self.ttl_seconds
        return True


@dataclass
class RequestEnvelope:
    action: str
    args: dict[str, Any]
    timestamp: str
    nonce: str
    request_id: str
    signature: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RequestEnvelope":
        args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        return cls(
            action=str(payload.get("action", "") or ""),
            args=args,
            timestamp=str(payload.get("timestamp", "") or ""),
            nonce=str(payload.get("nonce", "") or ""),
            request_id=str(payload.get("request_id", "") or ""),
            signature=str(payload.get("signature", "") or ""),
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_request_payload(
    *,
    action: str,
    args: dict[str, Any],
    timestamp: str,
    nonce: str,
    request_id: str,
) -> bytes:
    body = {
        "action": action,
        "args": args,
        "nonce": nonce,
        "request_id": request_id,
        "timestamp": timestamp,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_signature(
    *,
    action: str,
    args: dict[str, Any],
    timestamp: str,
    nonce: str,
    request_id: str,
    shared_secret: str,
) -> str:
    payload = canonical_request_payload(
        action=action,
        args=args,
        timestamp=timestamp,
        nonce=nonce,
        request_id=request_id,
    )
    return hmac.new(
        shared_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def build_signed_request(
    *,
    action: str,
    args: dict[str, Any] | None = None,
    shared_secret: str,
    timestamp: str | None = None,
    nonce: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    actual_args = args or {}
    actual_timestamp = timestamp or utc_now()
    actual_nonce = nonce or uuid.uuid4().hex
    actual_request_id = request_id or uuid.uuid4().hex
    signature = compute_signature(
        action=action,
        args=actual_args,
        timestamp=actual_timestamp,
        nonce=actual_nonce,
        request_id=actual_request_id,
        shared_secret=shared_secret,
    )
    return {
        "action": action,
        "args": actual_args,
        "timestamp": actual_timestamp,
        "nonce": actual_nonce,
        "request_id": actual_request_id,
        "signature": signature,
    }


def _parse_timestamp(raw: str) -> datetime:
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build_status_snapshot(
    config: PrivateOperatorChannelConfig,
    *,
    config_path: Path,
    config_exists: bool,
    include_authority: bool = True,
    include_bus: bool = True,
) -> dict[str, Any]:
    snapshot = config_snapshot(
        config,
        config_path=config_path,
        config_exists=config_exists,
        secret_present=bool(os.environ.get(config.shared_secret_env)),
    )
    if include_authority:
        snapshot["authority_gateway"] = authority_gateway_status()
    if include_bus:
        snapshot["project_os_bus"] = project_os_bus_status(timeout_seconds=0.25)
    snapshot["success"] = True
    snapshot["summary"] = (
        f"private operator channel @ {config.bind_host}:{config.port}; "
        f"effectful_actions={'on' if config.allow_effectful_actions else 'off'}; "
        f"tls={'on' if config.tls_enabled else 'off'}"
    )
    return snapshot


def dispatch_action(
    *,
    config: PrivateOperatorChannelConfig,
    config_path: Path,
    config_exists: bool,
    action: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    if action not in config.allowed_actions:
        return {
            "success": False,
            "error": "action_not_allowed",
            "action": action,
        }
    if action == "ping":
        return {"success": True, "summary": "pong", "action": action}
    if action == "status":
        return build_status_snapshot(
            config,
            config_path=config_path,
            config_exists=config_exists,
            include_authority=bool(args.get("include_authority", True)),
            include_bus=bool(args.get("include_bus", True)),
        )
    if action == "authority_status":
        return authority_gateway_status()
    if action == "bus_status":
        timeout_seconds = min(max(float(args.get("timeout_seconds", 0.25) or 0.25), 0.05), 5.0)
        return project_os_bus_status(timeout_seconds=timeout_seconds)
    if action == "tail_bus":
        seconds = min(max(float(args.get("seconds", 0.5) or 0.5), 0.05), 5.0)
        max_events = min(max(int(args.get("max_events", 10) or 10), 1), 50)
        topics = args.get("topics") if isinstance(args.get("topics"), list) else None
        return project_os_tail(topics=topics, seconds=seconds, max_events=max_events)
    if action == "android_open":
        target = str(args.get("target", "") or "").strip()
        browser = str(args.get("browser", "brave") or "brave")
        dry_run = bool(args.get("dry_run", False))
        if target not in config.allowed_android_targets:
            return {
                "success": False,
                "error": "target_not_allowed",
                "allowed_android_targets": list(config.allowed_android_targets),
            }
        if not dry_run and not config.allow_effectful_actions:
            return {
                "success": False,
                "error": "effectful_actions_disabled",
                "hint": "Enable allow_effectful_actions in the private operator channel config or send dry_run=true.",
            }
        return android_open(target=target, browser=browser, dry_run=dry_run)
    return {"success": False, "error": "unimplemented_action", "action": action}


class PrivateOperatorChannelRuntime:
    def __init__(
        self,
        *,
        config: PrivateOperatorChannelConfig,
        config_path: Path,
        config_exists: bool,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.config_exists = config_exists
        self.nonce_cache = NonceCache(ttl_seconds=max(config.max_skew_seconds, 1))
        self.audit_log_path = resolve_audit_log_path(config)

    def verify(self, envelope: RequestEnvelope) -> tuple[bool, str]:
        shared_secret = os.environ.get(self.config.shared_secret_env, "")
        if not shared_secret:
            return False, "missing_secret"
        if not envelope.action or not envelope.timestamp or not envelope.nonce or not envelope.request_id:
            return False, "invalid_envelope"
        try:
            request_time = _parse_timestamp(envelope.timestamp)
        except ValueError:
            return False, "invalid_timestamp"
        skew = abs((datetime.now(UTC) - request_time).total_seconds())
        if skew > self.config.max_skew_seconds:
            return False, "stale_timestamp"
        expected = compute_signature(
            action=envelope.action,
            args=envelope.args,
            timestamp=envelope.timestamp,
            nonce=envelope.nonce,
            request_id=envelope.request_id,
            shared_secret=shared_secret,
        )
        if not hmac.compare_digest(expected, envelope.signature):
            return False, "invalid_signature"
        if not self.nonce_cache.accept(envelope.nonce):
            return False, "replayed_nonce"
        return True, "ok"

    def append_audit(self, *, envelope: RequestEnvelope, outcome: dict[str, Any], code: str) -> None:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        audit_entry = {
            "timestamp": utc_now(),
            "request_id": envelope.request_id,
            "action": envelope.action,
            "nonce": envelope.nonce,
            "code": code,
            "success": bool(outcome.get("success", False)),
            "args": self._safe_args(envelope.action, envelope.args),
        }
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(audit_entry, sort_keys=True) + "\n")

    def handle_payload(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        envelope = RequestEnvelope.from_payload(payload)
        verified, code = self.verify(envelope)
        if not verified:
            result = {
                "success": False,
                "error": code,
                "request_id": envelope.request_id,
                "action": envelope.action,
            }
            self.append_audit(envelope=envelope, outcome=result, code=code)
            return (401 if code in _AUTH_FAILURE_CODES else 400), result
        result = dispatch_action(
            config=self.config,
            config_path=self.config_path,
            config_exists=self.config_exists,
            action=envelope.action,
            args=envelope.args,
        )
        result.setdefault("request_id", envelope.request_id)
        result.setdefault("action", envelope.action)
        self.append_audit(envelope=envelope, outcome=result, code="ok")
        return (200 if result.get("success", True) else 403), result

    @staticmethod
    def _safe_args(action: str, args: dict[str, Any]) -> dict[str, Any]:
        if action != "android_open":
            return args
        return {
            "target": args.get("target"),
            "browser": args.get("browser", "brave"),
            "dry_run": bool(args.get("dry_run", False)),
        }
