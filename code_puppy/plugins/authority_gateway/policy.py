from __future__ import annotations

import contextvars
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .anomaly import active_quarantine_reason, evaluate_runtime_anomalies
from .audit import emit_authority_event
from .constraints import lease_constraint_failure
from .identity import get_execution_identity
from .lease_store import LeaseRecord, consume_lease, list_matching_leases
from .shell_policy import assess_shell_command as assess_shell_policy_command

_RESERVED_LEASE: contextvars.ContextVar[LeaseRecord | None] = contextvars.ContextVar(
    "authority_gateway_reserved_lease", default=None
)
_RESERVED_TOOL: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "authority_gateway_reserved_tool", default=None
)
_RESERVED_CAPABILITY: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "authority_gateway_reserved_capability", default=None
)

ALLOWED_ANDROID_OPEN_TARGETS = {
    "brave",
    "chrome",
    "termux",
    "settings",
    "wifi",
    "wi-fi",
    "wireless",
    "wireless debugging",
    "developer options",
    "dev options",
    "bluetooth",
    "display",
    "sound",
    "battery",
    "security",
    "accessibility",
    "app settings",
}
ALLOWED_INTENT_ACTION_PREFIXES = (
    "android.intent.action.",
    "android.settings.",
)
BLOCKED_INTENT_FLAGS = {
    "FLAG_GRANT_READ_URI_PERMISSION",
    "FLAG_GRANT_WRITE_URI_PERMISSION",
}

TOOL_CAPABILITIES = {
    "android_browser_click_link_by_text": "android.browser.act",
    "android_browser_click_selector": "android.browser.act",
    "android_browser_fill_input": "android.browser.act",
    "android_browser_open_url": "android.browser.open_url",
    "android_browser_take_screenshot": "android.browser.capture",
    "android_capture_screenshot": "android.screen.capture",
    "android_handoff_file": "android.handoff.share",
    "android_handoff_text": "android.handoff.share",
    "android_handoff_url": "android.handoff.share",
    "android_input_keyevent": "android.ui.input",
    "android_input_swipe": "android.ui.input",
    "android_input_tap": "android.ui.input",
    "android_input_tap_bounds": "android.ui.input",
    "android_input_text": "android.ui.input",
    "android_intent_send": "android.intent.send",
    "android_launch_app": "android.app.launch",
    "android_notification_send": "android.notification.post",
    "android_open": "android.app.open",
    "android_open_notification_settings": "android.settings.open",
    "android_open_settings": "android.settings.open",
    "android_record_screen": "android.screen.capture",
    "android_share_text": "android.handoff.share",
    "android_ui_tap_match": "android.ui.input",
    "android_ui_text_into_match": "android.ui.input",
}


@dataclass(frozen=True)
class PolicyDecision:
    blocked: bool = False
    reason: str = ""
    capability: str | None = None
    lease_required: bool = False


def _normalize_text(value: str) -> str:
    return " ".join(
        (value or "").strip().lower().replace("_", " ").replace("-", " ").split()
    )


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _block(reason: str) -> PolicyDecision:
    return PolicyDecision(blocked=True, reason=reason)


def _allow() -> PolicyDecision:
    return PolicyDecision()


def _require_lease(capability: str, reason: str) -> PolicyDecision:
    return PolicyDecision(capability=capability, lease_required=True, reason=reason)


def _is_dry_run(tool_args: dict[str, Any]) -> bool:
    return bool(tool_args.get("dry_run"))


def _tracked_tool(tool_name: str) -> bool:
    return tool_name == "agent_run_shell_command" or tool_name in TOOL_CAPABILITIES


def _summarize_tool_args(tool_args: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in tool_args.items():
        if key in {"text", "value"}:
            summary[f"{key}_length"] = len(str(value))
        elif key in {"command", "selector", "target", "url", "file_path", "bounds"}:
            text = str(value)
            summary[key] = text if len(text) <= 180 else text[:177] + "..."
        elif key in {
            "browser",
            "page",
            "action",
            "package_name",
            "activity_name",
            "dispatch_mode",
            "dry_run",
            "background",
            "artifact_name",
            "keycode",
            "submit",
            "cwd",
        }:
            summary[key] = value
    if not summary:
        summary["keys"] = sorted(tool_args.keys())
    return summary


def _maybe_trip_circuit_breaker(principal_id: str) -> str | None:
    anomaly = evaluate_runtime_anomalies(principal_id=principal_id)
    if not anomaly.tripped:
        return None
    _clear_reservation()
    return anomaly.reason


def assess_shell_command(command: str, *, cwd: str = "") -> PolicyDecision:
    decision = assess_shell_policy_command(command, cwd=cwd)
    return PolicyDecision(
        blocked=decision.blocked,
        reason=decision.reason,
        capability=decision.capability,
        lease_required=decision.lease_required,
    )


def _outputs_only(file_path: str) -> bool:
    path = Path(file_path).expanduser().resolve()
    outputs_dir = (Path.cwd() / "outputs").resolve()
    try:
        path.relative_to(outputs_dir)
        return True
    except ValueError:
        return False


def _evaluate_intent(tool_args: dict[str, Any]) -> PolicyDecision:
    if _is_dry_run(tool_args):
        return _allow()

    dispatch_mode = str(tool_args.get("dispatch_mode", "start")).strip().lower()
    if dispatch_mode == "broadcast":
        return _block(
            "[BLOCKED] Broadcast intents are disabled until an explicit allowlist exists."
        )

    flags = tool_args.get("flags") or []
    if flags:
        normalized_flags = {str(flag).strip() for flag in flags}
        if normalized_flags & BLOCKED_INTENT_FLAGS or normalized_flags:
            return _block(
                "[BLOCKED] Intent flags are not allowed by deterministic policy yet."
            )

    action = str(tool_args.get("action", "")).strip()
    if action and not action.startswith(ALLOWED_INTENT_ACTION_PREFIXES):
        return _block(
            "[BLOCKED] Intent action is outside the vetted Android allowlist."
        )

    package_name = str(tool_args.get("package_name", "")).strip()
    activity_name = str(tool_args.get("activity_name", "")).strip()
    if (
        not package_name
        and not activity_name
        and action != "android.intent.action.VIEW"
    ):
        return _block(
            "[BLOCKED] Live intents must target an explicit package/activity unless they are simple VIEW launches."
        )

    return _require_lease(
        "android.intent.send",
        "Live Android IPC requires an active execution lease.",
    )


def _evaluate_android_open(tool_args: dict[str, Any]) -> PolicyDecision:
    if _is_dry_run(tool_args):
        return _allow()

    target = str(tool_args.get("target", "")).strip()
    browser = str(tool_args.get("browser", "brave")).strip().lower()
    if _looks_like_url(target):
        if browser == "system":
            return _block(
                "[BLOCKED] System-browser URL launches are disallowed; use an explicit browser package."
            )
        return _require_lease(
            "android.browser.open_url",
            "Live browser launches require an active execution lease.",
        )

    if _normalize_text(target) not in ALLOWED_ANDROID_OPEN_TARGETS:
        return _block(
            "[BLOCKED] android_open only allows built-in shortcut targets in live mode."
        )

    return _require_lease(
        "android.app.open",
        "Launching apps or settings through android_open requires an active execution lease.",
    )


def evaluate_tool_call(tool_name: str, tool_args: dict[str, Any]) -> PolicyDecision:
    if tool_name == "agent_run_shell_command":
        return assess_shell_command(
            str(tool_args.get("command", "")),
            cwd=str(tool_args.get("cwd", "") or ""),
        )

    if tool_name == "android_intent_send":
        return _evaluate_intent(tool_args)

    if tool_name == "android_handoff_file":
        if _is_dry_run(tool_args):
            return _allow()
        file_path = str(tool_args.get("file_path", "")).strip()
        if not file_path or not _outputs_only(file_path):
            return _block(
                "[BLOCKED] File handoff is restricted to the repo outputs/ directory."
            )

    if tool_name == "android_browser_open_url":
        if _is_dry_run(tool_args):
            return _allow()
        browser = str(tool_args.get("browser", "brave")).strip().lower()
        if browser == "system":
            return _block(
                "[BLOCKED] System-browser URL launches are disallowed; use brave or chrome explicitly."
            )

    if tool_name == "android_open":
        return _evaluate_android_open(tool_args)

    if tool_name in {
        "android_handoff_text",
        "android_handoff_url",
        "android_input_keyevent",
        "android_input_swipe",
        "android_input_tap",
        "android_input_tap_bounds",
        "android_input_text",
        "android_notification_send",
        "android_capture_screenshot",
        "android_record_screen",
    } and _is_dry_run(tool_args):
        return _allow()

    capability = TOOL_CAPABILITIES.get(tool_name)
    if capability is None:
        return _allow()

    reason = f"Tool {tool_name} requires an active execution lease for capability {capability}."
    return _require_lease(capability, reason)


def _reserve_lease(
    record: LeaseRecord | None, tool_name: str, capability: str | None = None
) -> None:
    _RESERVED_LEASE.set(record)
    _RESERVED_TOOL.set(tool_name)
    _RESERVED_CAPABILITY.set(capability)


def _clear_reservation() -> None:
    _RESERVED_LEASE.set(None)
    _RESERVED_TOOL.set(None)
    _RESERVED_CAPABILITY.set(None)


def build_pre_tool_response(
    tool_name: str, tool_args: dict[str, Any]
) -> dict[str, Any] | None:
    principal_id = get_execution_identity().authority_principal_id
    tracked = _tracked_tool(tool_name)
    details = {"tool_args": _summarize_tool_args(tool_args)}

    quarantine_reason = active_quarantine_reason(principal_id=principal_id)
    if tracked and quarantine_reason:
        _clear_reservation()
        emit_authority_event(
            "tool_blocked",
            principal_id=principal_id,
            tool_name=tool_name,
            outcome="blocked",
            reason=quarantine_reason,
            details={**details, "block_kind": "quarantine"},
        )
        return {
            "blocked": True,
            "error_message": quarantine_reason,
            "reason": quarantine_reason,
        }

    decision = evaluate_tool_call(tool_name, tool_args)

    if decision.blocked:
        _clear_reservation()
        if tracked:
            emit_authority_event(
                "tool_blocked",
                principal_id=principal_id,
                capability=decision.capability,
                tool_name=tool_name,
                outcome="blocked",
                reason=decision.reason,
                details={**details, "block_kind": "policy"},
            )
            anomaly_reason = _maybe_trip_circuit_breaker(principal_id)
            if anomaly_reason:
                return {
                    "blocked": True,
                    "error_message": anomaly_reason,
                    "reason": anomaly_reason,
                }
        return {
            "blocked": True,
            "error_message": decision.reason,
            "reason": decision.reason,
        }

    if not decision.lease_required or not decision.capability:
        _clear_reservation()
        if tracked:
            emit_authority_event(
                "tool_allowed",
                principal_id=principal_id,
                tool_name=tool_name,
                outcome="allowed",
                reason=decision.reason
                or "Tool allowed by deterministic authority policy.",
                details=details,
            )
        return None

    leases = list_matching_leases(
        capability=decision.capability,
        tool_name=tool_name,
        principal_id=principal_id,
    )
    if not leases:
        _clear_reservation()
        reason = (
            "[BLOCKED] This action requires an active execution lease "
            f"for capability {decision.capability}."
        )
        emit_authority_event(
            "tool_blocked",
            principal_id=principal_id,
            capability=decision.capability,
            tool_name=tool_name,
            outcome="blocked",
            reason=reason,
            details={**details, "block_kind": "lease_missing"},
        )
        anomaly_reason = _maybe_trip_circuit_breaker(principal_id)
        if anomaly_reason:
            return {
                "blocked": True,
                "error_message": anomaly_reason,
                "reason": anomaly_reason,
            }
        return {
            "blocked": True,
            "error_message": reason,
            "reason": decision.reason,
        }

    lease: LeaseRecord | None = None
    constraint_reason: str | None = None
    for candidate in leases:
        constraint_reason = lease_constraint_failure(
            candidate,
            tool_name=tool_name,
            tool_args=tool_args,
        )
        if constraint_reason is None:
            lease = candidate
            break

    if lease is None:
        _clear_reservation()
        reason = constraint_reason or (
            "[BLOCKED] No active execution lease satisfied the requested runtime "
            "constraints."
        )
        emit_authority_event(
            "tool_blocked",
            principal_id=principal_id,
            lease_id=leases[0].lease_id,
            capability=decision.capability,
            tool_name=tool_name,
            outcome="blocked",
            reason=reason,
            details={
                **details,
                "block_kind": "constraint",
                "lease_constraints": leases[0].constraints,
            },
        )
        anomaly_reason = _maybe_trip_circuit_breaker(principal_id)
        return {
            "blocked": True,
            "error_message": anomaly_reason or reason,
            "reason": anomaly_reason or decision.reason,
        }

    _reserve_lease(lease, tool_name, decision.capability)
    emit_authority_event(
        "tool_allowed",
        principal_id=principal_id,
        lease_id=lease.lease_id,
        capability=decision.capability,
        tool_name=tool_name,
        outcome="leased",
        reason="Tool allowed under an active capability-scoped lease.",
        details={
            **details,
            "lease_constraints": lease.constraints,
        },
    )
    anomaly_reason = _maybe_trip_circuit_breaker(principal_id)
    if anomaly_reason:
        return {
            "blocked": True,
            "error_message": anomaly_reason,
            "reason": anomaly_reason,
        }
    return None


def _result_success(result: Any) -> bool:
    if isinstance(result, dict) and "success" in result:
        return bool(result.get("success"))
    if hasattr(result, "success"):
        return bool(getattr(result, "success"))
    if isinstance(result, str) and result.startswith("ERROR:"):
        return False
    return True


def handle_post_tool_result(tool_name: str, result: Any) -> None:
    lease = _RESERVED_LEASE.get()
    reserved_tool = _RESERVED_TOOL.get()
    capability = _RESERVED_CAPABILITY.get()
    principal_id = get_execution_identity().authority_principal_id
    try:
        if lease is None or reserved_tool != tool_name:
            return
        if _result_success(result):
            updated = consume_lease(lease, capability=capability, tool_name=tool_name)
            emit_authority_event(
                "lease_consumed",
                principal_id=principal_id,
                lease_id=updated.lease_id,
                capability=capability,
                tool_name=tool_name,
                outcome="consumed",
                reason="Successful effectful tool execution consumed lease budget.",
                details={
                    "status": updated.status,
                    "remaining_uses": updated.remaining_uses,
                    "quotas": updated.quotas,
                },
            )
        else:
            emit_authority_event(
                "tool_failed",
                principal_id=principal_id,
                lease_id=lease.lease_id,
                capability=capability,
                tool_name=tool_name,
                outcome="failed",
                reason="Tool failed after lease reservation; lease was left active.",
                details={},
            )
    finally:
        _clear_reservation()


def reservation_debug_state() -> dict[str, Any]:
    lease = _RESERVED_LEASE.get()
    return {
        "reserved_tool": _RESERVED_TOOL.get(),
        "reserved_capability": _RESERVED_CAPABILITY.get(),
        "lease_id": None if lease is None else lease.lease_id,
    }
