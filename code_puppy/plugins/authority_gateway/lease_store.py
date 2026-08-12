from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from shutil import move
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .identity import get_authority_principal_id

DEFAULT_EYES_ROOT = Path.home() / ".project_os" / "eyes"
LEGACY_SCOPE_CAPABILITIES: dict[str, set[str]] = {
    "single_harmless_action": {
        "android.app.launch",
        "android.browser.open_url",
        "android.notification.post",
        "android.settings.open",
    }
}
SUPPORTED_CONSTRAINT_KEYS = {
    "allowed_paths",
    "intent_actions",
    "intent_packages",
    "browser_packages",
    "android_packages",
}
CONSTRAINT_KEY_ALIASES = {
    "allowed_packages": "android_packages",
}
LEGACY_CAPABILITY_ALIASES: dict[str, set[str]] = {
    "shell.exec": {
        "shell.repo.write",
        "shell.process.exec",
        "network.lan.connect",
        "adb.wireless.connect",
    }
}
LEASE_BUCKET_BY_STATUS = {
    "active": "active",
    "expired": "expired",
    "used": "completed",
    "revoked": "failed",
    "failed": "failed",
}


@dataclass(frozen=True)
class LeaseRecord:
    path: Path
    payload: dict[str, Any]

    @property
    def lease_id(self) -> str:
        return str(self.payload.get("lease_id", self.path.stem))

    @property
    def principal_id(self) -> str | None:
        raw = self.payload.get("principal_id")
        if raw in (None, "", "*"):
            return None
        return str(raw)

    @property
    def status(self) -> str:
        return str(self.payload.get("status", ""))

    @property
    def not_before(self) -> dt.datetime | None:
        return _parse_dt(self.payload.get("not_before"))

    @property
    def expires_at(self) -> dt.datetime | None:
        return _parse_dt(self.payload.get("expires_at"))

    @property
    def capabilities(self) -> list[str]:
        raw = self.payload.get("capabilities")
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
        return []

    @property
    def allowed_tools(self) -> list[str]:
        raw = self.payload.get("allowed_tools")
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
        return []

    @property
    def constraints(self) -> dict[str, Any]:
        raw = self.payload.get("constraints")
        if isinstance(raw, dict):
            return dict(raw)
        return {}

    @property
    def quotas(self) -> dict[str, Any]:
        raw = self.payload.get("quotas")
        if isinstance(raw, dict):
            return dict(raw)
        return {
            "max_uses": int(self.payload.get("max_uses", 0) or 0),
            "remaining_uses": int(self.payload.get("remaining_uses", 0) or 0),
            "max_tool_calls": None,
            "max_shell_commands": None,
            "max_token_spend": None,
            "tool_calls_used": 0,
            "shell_commands_used": 0,
            "token_spend_used": 0,
        }

    @property
    def delegation(self) -> dict[str, Any]:
        raw = self.payload.get("delegation")
        if isinstance(raw, dict):
            return dict(raw)
        return {
            "mode": "direct",
            "requested_by_actor_id": None,
            "delegated_by_actor_id": None,
            "delegated_to_actor_ids": [],
            "run_id": None,
        }

    @property
    def remaining_uses(self) -> int:
        return int(self.quotas.get("remaining_uses", 0) or 0)


def _parse_dt(raw: Any) -> dt.datetime | None:
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def get_default_principal_id() -> str:
    return get_authority_principal_id()


def get_eyes_root() -> Path:
    raw = os.environ.get("PROJECT_OS_EYES_ROOT") or os.environ.get(
        "SHARPEDGE_EYES_ROOT"
    )
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_EYES_ROOT


def get_leases_root() -> Path:
    return get_eyes_root() / "leases"


def _lease_bucket_dir(bucket: str) -> Path:
    return get_leases_root() / bucket


def get_active_leases_dir() -> Path:
    return _lease_bucket_dir("active")


def get_completed_leases_dir() -> Path:
    return _lease_bucket_dir("completed")


def get_expired_leases_dir() -> Path:
    return _lease_bucket_dir("expired")


def get_failed_leases_dir() -> Path:
    return _lease_bucket_dir("failed")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _quota_value(payload: dict[str, Any], key: str) -> int | None:
    quotas = payload.get("quotas") if isinstance(payload.get("quotas"), dict) else None
    if quotas is None:
        return None
    value = quotas.get(key)
    if value is None:
        return None
    return int(value)


def _clean_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in cleaned:
            continue
        cleaned.append(text)
    return cleaned


def _normalize_constraints(raw: dict[str, Any] | None) -> dict[str, Any]:
    if raw in (None, {}):
        return {}
    if not isinstance(raw, dict):
        raise ValueError("constraints must be a JSON object")

    canonicalized: dict[str, Any] = {}
    for key, value in raw.items():
        canonical_key = CONSTRAINT_KEY_ALIASES.get(key, key)
        canonicalized[canonical_key] = value

    unknown = sorted(set(canonicalized) - SUPPORTED_CONSTRAINT_KEYS)
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"unsupported constraint keys: {joined}")

    normalized: dict[str, Any] = {}
    for key in sorted(SUPPORTED_CONSTRAINT_KEYS):
        values = _clean_string_list(canonicalized.get(key))
        if values:
            normalized[key] = values
    return normalized


def _positive_int(value: Any, *, field_name: str) -> int:
    number = int(value)
    if number <= 0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _optional_nonnegative_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    number = int(value)
    if number < 0:
        raise ValueError(f"{field_name} must be zero or positive")
    return number


def _normalize_delegation(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = raw or {}
    if not isinstance(payload, dict):
        raise ValueError("delegation must be a JSON object")
    mode = str(payload.get("mode", "direct") or "direct").strip() or "direct"
    if mode not in {"direct", "shared_authority"}:
        raise ValueError("delegation.mode must be direct or shared_authority")
    requested_by_actor_id = payload.get("requested_by_actor_id")
    delegated_by_actor_id = payload.get("delegated_by_actor_id")
    run_id = payload.get("run_id")
    return {
        "mode": mode,
        "requested_by_actor_id": (
            str(requested_by_actor_id).strip() if requested_by_actor_id else None
        ),
        "delegated_by_actor_id": (
            str(delegated_by_actor_id).strip() if delegated_by_actor_id else None
        ),
        "delegated_to_actor_ids": _clean_string_list(
            payload.get("delegated_to_actor_ids") or []
        ),
        "run_id": str(run_id).strip() if run_id else None,
    }


def _lease_bucket_for_status(status: str) -> str:
    return LEASE_BUCKET_BY_STATUS.get(str(status or "").strip() or "failed", "failed")


def _lease_storage_path(path: Path, payload: dict[str, Any]) -> Path:
    lease_id = str(payload.get("lease_id", path.stem)).strip() or path.stem
    bucket = _lease_bucket_for_status(str(payload.get("status", "active")))
    return _lease_bucket_dir(bucket) / f"{lease_id}.json"


def _persist_lease_payload(path: Path, payload: dict[str, Any]) -> LeaseRecord:
    target_path = _lease_storage_path(path, payload)
    _write_json(target_path, payload)
    if path != target_path and path.exists():
        path.unlink(missing_ok=True)
    return LeaseRecord(path=target_path, payload=payload)


def _archive_invalid_active_lease(path: Path) -> Path:
    target = get_failed_leases_dir() / path.name
    if target.exists():
        target = target.with_name(f"{path.stem}-{uuid.uuid4().hex[:8]}{path.suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    move(str(path), str(target))
    return target


def lease_store_inventory() -> dict[str, int]:
    buckets = {
        "active": get_active_leases_dir(),
        "completed": get_completed_leases_dir(),
        "expired": get_expired_leases_dir(),
        "failed": get_failed_leases_dir(),
    }
    return {
        name: len(list(directory.glob("*.json"))) if directory.is_dir() else 0
        for name, directory in buckets.items()
    }


def mint_lease(
    *,
    principal_id: str,
    capabilities: list[str],
    reason: str,
    granted_by: str = "operator",
    allowed_tools: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
    ttl_seconds: int = 3600,
    max_uses: int = 25,
    max_tool_calls: int | None = None,
    max_shell_commands: int | None = None,
    lease_id: str = "",
    delegation: dict[str, Any] | None = None,
) -> LeaseRecord:
    principal = principal_id.strip()
    if not principal:
        raise ValueError("principal_id is required")

    cleaned_capabilities = _clean_string_list(capabilities)
    if not cleaned_capabilities:
        raise ValueError("capabilities must contain at least one value")

    cleaned_allowed_tools = _clean_string_list(allowed_tools or [])
    normalized_constraints = _normalize_constraints(constraints)
    normalized_delegation = _normalize_delegation(delegation)
    ttl_value = _positive_int(ttl_seconds, field_name="ttl_seconds")
    max_uses_value = _positive_int(max_uses, field_name="max_uses")
    max_tool_calls_value = _optional_nonnegative_int(
        max_tool_calls, field_name="max_tool_calls"
    )
    max_shell_commands_value = _optional_nonnegative_int(
        max_shell_commands, field_name="max_shell_commands"
    )

    resolved_lease_id = (lease_id or f"lease-{uuid.uuid4().hex[:12]}").strip()
    if not resolved_lease_id:
        raise ValueError("lease_id cannot be blank")

    path = get_active_leases_dir() / f"{resolved_lease_id}.json"
    if _lease_storage_path(
        path, {"lease_id": resolved_lease_id, "status": "active"}
    ).exists():
        raise ValueError(f"lease_id '{resolved_lease_id}' already exists")

    now = _now()
    payload = {
        "lease_id": resolved_lease_id,
        "principal_id": principal,
        "capabilities": cleaned_capabilities,
        "allowed_tools": cleaned_allowed_tools,
        "constraints": normalized_constraints,
        "delegation": normalized_delegation,
        "status": "active",
        "issued_by": granted_by,
        "grant_reason": reason,
        "created_at": now.isoformat(),
        "not_before": now.isoformat(),
        "expires_at": (now + dt.timedelta(seconds=ttl_value)).isoformat(),
        "last_used_at": None,
        "revoked_at": None,
        "revoked_by": None,
        "revocation_reason": None,
        "minted_event_ref": None,
        "quotas": {
            "max_uses": max_uses_value,
            "remaining_uses": max_uses_value,
            "max_tool_calls": max_tool_calls_value,
            "max_shell_commands": max_shell_commands_value,
            "max_token_spend": None,
            "tool_calls_used": 0,
            "shell_commands_used": 0,
            "token_spend_used": 0,
        },
    }
    return _persist_lease_payload(path, payload)


def _usage_limit_reached(payload: dict[str, Any]) -> bool:
    if int(_quota_value(payload, "remaining_uses") or 0) <= 0:
        return True

    max_tool_calls = _quota_value(payload, "max_tool_calls")
    tool_calls_used = int(_quota_value(payload, "tool_calls_used") or 0)
    if max_tool_calls is not None and tool_calls_used >= max_tool_calls:
        return True

    max_shell_commands = _quota_value(payload, "max_shell_commands")
    shell_commands_used = int(_quota_value(payload, "shell_commands_used") or 0)
    if max_shell_commands is not None and shell_commands_used >= max_shell_commands:
        return True

    legacy_remaining = payload.get("remaining_uses")
    if legacy_remaining is not None and int(legacy_remaining or 0) <= 0:
        return True
    return False


def _mark_status(path: Path, payload: dict[str, Any], status: str) -> LeaseRecord:
    updated = dict(payload)
    updated["status"] = status
    return _persist_lease_payload(path, updated)


def _refresh_lease_state(record: LeaseRecord) -> LeaseRecord | None:
    payload = dict(record.payload)
    if str(payload.get("status", "")) != "active":
        return _persist_lease_payload(record.path, payload)

    now = _now()
    if record.not_before and record.not_before > now:
        return None
    if record.expires_at and record.expires_at <= now:
        return _mark_status(record.path, payload, "expired")
    if _usage_limit_reached(payload):
        return _mark_status(record.path, payload, "used")
    return record


def iter_active_leases() -> Iterable[LeaseRecord]:
    leases_dir = get_active_leases_dir()
    if not leases_dir.is_dir():
        return []

    records: list[LeaseRecord] = []
    for path in sorted(leases_dir.glob("*.json")):
        try:
            record = LeaseRecord(path=path, payload=_read_json(path))
            refreshed = _refresh_lease_state(record)
            if refreshed is None:
                records.append(record)
                continue
            if refreshed.status == "active":
                records.append(refreshed)
        except Exception:
            _archive_invalid_active_lease(path)
            continue
    return records


def lease_allows(
    record: LeaseRecord,
    *,
    capability: str,
    tool_name: str,
    principal_id: str | None = None,
) -> bool:
    if principal_id and record.principal_id and record.principal_id != principal_id:
        return False

    if record.allowed_tools and tool_name not in record.allowed_tools:
        return False

    if capability in record.capabilities:
        return True
    for granted_capability in record.capabilities:
        if capability in LEGACY_CAPABILITY_ALIASES.get(granted_capability, set()):
            return True

    lease_scope = str(record.payload.get("lease_scope", "")).strip()
    if not lease_scope:
        return False
    if lease_scope == capability:
        return True
    return capability in LEGACY_SCOPE_CAPABILITIES.get(lease_scope, set())


def reconcile_lease_store() -> dict[str, Any]:
    active_dir = get_active_leases_dir()
    scanned = 0
    moved: list[dict[str, str]] = []
    invalid_files: list[str] = []
    for path in sorted(active_dir.glob("*.json")) if active_dir.is_dir() else []:
        scanned += 1
        try:
            record = LeaseRecord(path=path, payload=_read_json(path))
            refreshed = _refresh_lease_state(record)
            if refreshed is None or refreshed.status == "active":
                continue
            moved.append(
                {
                    "lease_id": refreshed.lease_id,
                    "status": refreshed.status,
                    "bucket": _lease_bucket_for_status(refreshed.status),
                }
            )
        except Exception:
            invalid_files.append(str(_archive_invalid_active_lease(path)))
    return {
        "success": True,
        "scanned": scanned,
        "moved_count": len(moved),
        "moved": moved,
        "invalid_file_count": len(invalid_files),
        "invalid_files": invalid_files,
        "inventory": lease_store_inventory(),
    }


def list_matching_leases(
    *,
    capability: str,
    tool_name: str,
    principal_id: str | None = None,
) -> list[LeaseRecord]:
    matches = [
        record
        for record in iter_active_leases()
        if lease_allows(
            record,
            capability=capability,
            tool_name=tool_name,
            principal_id=principal_id,
        )
    ]
    matches.sort(
        key=lambda record: (
            record.expires_at or dt.datetime.max.replace(tzinfo=dt.timezone.utc)
        )
    )
    return matches


def find_matching_lease(
    *,
    capability: str,
    tool_name: str,
    principal_id: str | None = None,
) -> LeaseRecord | None:
    matches = list_matching_leases(
        capability=capability,
        tool_name=tool_name,
        principal_id=principal_id,
    )
    return matches[0] if matches else None


def consume_lease(
    record: LeaseRecord,
    *,
    capability: str | None = None,
    tool_name: str | None = None,
) -> LeaseRecord:
    payload = _read_json(record.path)
    payload["last_used_at"] = _now().isoformat()

    quotas = payload.get("quotas") if isinstance(payload.get("quotas"), dict) else None
    if quotas is not None:
        quotas = dict(quotas)
        quotas["tool_calls_used"] = int(quotas.get("tool_calls_used", 0) or 0) + 1
        if tool_name == "agent_run_shell_command":
            quotas["shell_commands_used"] = (
                int(quotas.get("shell_commands_used", 0) or 0) + 1
            )
        quotas["remaining_uses"] = max(
            0,
            int(quotas.get("remaining_uses", quotas.get("max_uses", 0)) or 0) - 1,
        )
        payload["quotas"] = quotas
    else:
        remaining = int(payload.get("remaining_uses", 0) or 0)
        payload["remaining_uses"] = max(0, remaining - 1)

    if _usage_limit_reached(payload):
        payload["status"] = "used"

    return _persist_lease_payload(record.path, payload)


def revoke_lease(
    record: LeaseRecord,
    *,
    reason: str,
    revoked_by: str = "system",
) -> LeaseRecord:
    payload = _read_json(record.path)
    payload["status"] = "revoked"
    payload["revoked_at"] = _now().isoformat()
    payload["revoked_by"] = revoked_by
    payload["revocation_reason"] = reason
    return _persist_lease_payload(record.path, payload)


def revoke_all_active_leases(
    *,
    reason: str,
    revoked_by: str = "system",
    principal_id: str | None = None,
) -> list[LeaseRecord]:
    revoked: list[LeaseRecord] = []
    for record in iter_active_leases():
        if principal_id and record.principal_id and record.principal_id != principal_id:
            continue
        revoked.append(revoke_lease(record, reason=reason, revoked_by=revoked_by))
    return revoked
