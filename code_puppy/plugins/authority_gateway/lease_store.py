from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_EYES_ROOT = Path.home() / ".project_os" / "eyes"
DEFAULT_PRINCIPAL_ID = os.environ.get("PROJECT_OS_PRINCIPAL_ID", "code-puppy-41abae")
LEGACY_SCOPE_CAPABILITIES: dict[str, set[str]] = {
    "single_harmless_action": {
        "android.app.launch",
        "android.browser.open_url",
        "android.notification.post",
        "android.settings.open",
    }
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
    return os.environ.get("PROJECT_OS_PRINCIPAL_ID", DEFAULT_PRINCIPAL_ID)


def get_eyes_root() -> Path:
    raw = os.environ.get("PROJECT_OS_EYES_ROOT") or os.environ.get(
        "SHARPEDGE_EYES_ROOT"
    )
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_EYES_ROOT


def get_active_leases_dir() -> Path:
    return get_eyes_root() / "leases" / "active"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
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
    _write_json(path, updated)
    return LeaseRecord(path=path, payload=updated)


def _refresh_lease_state(record: LeaseRecord) -> LeaseRecord | None:
    payload = dict(record.payload)
    if str(payload.get("status", "")) != "active":
        return None

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
            if refreshed is not None and refreshed.status == "active":
                records.append(refreshed)
        except Exception:
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

    if tool_name in record.allowed_tools:
        return True
    if capability in record.capabilities:
        return True

    lease_scope = str(record.payload.get("lease_scope", "")).strip()
    if not lease_scope:
        return False
    if lease_scope == capability:
        return True
    return capability in LEGACY_SCOPE_CAPABILITIES.get(lease_scope, set())


def find_matching_lease(
    *,
    capability: str,
    tool_name: str,
    principal_id: str | None = None,
) -> LeaseRecord | None:
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
    if not matches:
        return None
    matches.sort(
        key=lambda record: (
            record.expires_at or dt.datetime.max.replace(tzinfo=dt.timezone.utc)
        )
    )
    return matches[0]


def consume_lease(
    record: LeaseRecord,
    *,
    capability: str | None = None,
    tool_name: str | None = None,
) -> LeaseRecord:
    del tool_name
    payload = _read_json(record.path)
    payload["last_used_at"] = _now().isoformat()

    quotas = payload.get("quotas") if isinstance(payload.get("quotas"), dict) else None
    if quotas is not None:
        quotas = dict(quotas)
        quotas["tool_calls_used"] = int(quotas.get("tool_calls_used", 0) or 0) + 1
        if capability == "shell.exec":
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

    _write_json(record.path, payload)
    return LeaseRecord(path=record.path, payload=payload)


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
    _write_json(record.path, payload)
    return LeaseRecord(path=record.path, payload=payload)


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
