from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..android_utility_kit.tooling import android_share_text

OUTPUT_DIR = Path("outputs")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bundle_candidates() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    candidates = [
        path for path in OUTPUT_DIR.glob("*support_bundle*.json") if path.is_file()
    ]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def _resolve_bundle_path(bundle_path: str = "") -> Path:
    if bundle_path.strip():
        path = Path(bundle_path)
        if not path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")
        return path
    candidates = _bundle_candidates()
    if not candidates:
        raise FileNotFoundError("No support bundle JSON files were found in outputs/")
    return candidates[0]


def _load_bundle(bundle_path: str = "") -> tuple[Path, dict[str, Any]]:
    path = _resolve_bundle_path(bundle_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Support bundle JSON did not contain an object")
    return path, data


def _section_present(bundle: dict[str, Any], key: str) -> bool:
    return (bundle.get("sections") or {}).get(key) is not None


def _extract_setup_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    setup = ((bundle.get("sections") or {}).get("setup") or {}).get("value") or {}
    return (setup.get("summary") or {}) if isinstance(setup, dict) else {}


def _extract_workflow_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    workflow = ((bundle.get("sections") or {}).get("workflow") or {}).get("value") or {}
    return (workflow.get("summary") or {}) if isinstance(workflow, dict) else {}


def _derive_health_notes(bundle: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    connected = int(bundle.get("connected_adb_devices") or 0)
    setup = _extract_setup_summary(bundle)
    workflow = _extract_workflow_summary(bundle)

    if connected <= 0:
        notes.append("ADB was not connected when the bundle was collected.")
    else:
        notes.append(f"ADB was connected with {connected} device(s) during collection.")

    if setup.get("notification_command_installed") is False:
        notes.append(
            "Direct Termux notification posting is not installed yet; fallback behavior may be in use."
        )

    if workflow.get("brave_installed"):
        notes.append(
            "Brave is installed and available for browser-oriented DroidPuppy flows."
        )

    if _section_present(bundle, "screenshot"):
        notes.append(
            "A screenshot artifact was captured as part of the support bundle."
        )
    else:
        notes.append("No screenshot was included in this bundle.")

    if _section_present(bundle, "logcat"):
        notes.append("Recent logcat data was included.")
    else:
        notes.append("No logcat section was included in this bundle.")

    if _section_present(bundle, "dumpsys"):
        notes.append("A dumpsys snapshot was included.")
    else:
        notes.append("No dumpsys snapshot was included in this bundle.")

    return notes


def _issue_title(bundle: dict[str, Any], path: Path) -> str:
    connected = int(bundle.get("connected_adb_devices") or 0)
    return f"Support bundle review: {path.stem} (adb_devices={connected})"


def _render_share_message(
    path: Path, bundle: dict[str, Any], recipient_hint: str = ""
) -> str:
    setup = _extract_setup_summary(bundle)
    workflow = _extract_workflow_summary(bundle)
    included = [
        key
        for key, value in (bundle.get("sections") or {}).items()
        if value is not None
    ]
    lines = [
        "DroidPuppy support bundle ready.",
        f"Bundle: {path}",
        f"Created: {bundle.get('created_at', 'unknown')}",
        f"ADB devices during collection: {bundle.get('connected_adb_devices', 0)}",
        f"Included sections: {', '.join(included) if included else 'none'}",
        f"Android available: {setup.get('android')}",
        f"Termux available: {setup.get('termux')}",
        f"ADB installed: {setup.get('adb_installed')}",
    ]
    if workflow:
        lines.append(
            f"Friendly shortcut count: {workflow.get('friendly_shortcut_count', 'unknown')}"
        )
    if recipient_hint.strip():
        lines.append(f"Recipient/context: {recipient_hint}")
    lines.append("Notes:")
    for note in _derive_health_notes(bundle):
        lines.append(f"- {note}")
    lines.append(
        "Next step: review the bundle JSON and decide whether a fresh reconnect + richer capture is needed."
    )
    return "\n".join(lines)


def _render_issue_body(path: Path, bundle: dict[str, Any]) -> str:
    included = [
        key
        for key, value in (bundle.get("sections") or {}).items()
        if value is not None
    ]
    notes = _derive_health_notes(bundle)
    lines = [
        "## Summary",
        "A DroidPuppy support bundle was collected for review.",
        "",
        "## Artifact",
        f"- Bundle path: `{path}`",
        f"- Created at: `{bundle.get('created_at', 'unknown')}`",
        f"- Connected ADB devices: `{bundle.get('connected_adb_devices', 0)}`",
        "",
        "## Included Sections",
    ]
    for name in included:
        lines.append(f"- `{name}`")
    if not included:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Notes",
        ]
    )
    for note in notes:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Requested Review",
            "- Confirm whether the current bundle is enough to diagnose the issue.",
            "- If not, advise whether we should reconnect ADB and re-run with screenshot/logcat/dumpsys enabled.",
        ]
    )
    return "\n".join(lines)


def android_support_bundle_list(max_results: int = 10) -> dict[str, Any]:
    candidates = _bundle_candidates()[: max(1, int(max_results))]
    return {
        "success": True,
        "count": len(candidates),
        "bundles": [
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "modified_epoch": path.stat().st_mtime,
            }
            for path in candidates
        ],
    }


def android_support_bundle_summarize(bundle_path: str = "") -> dict[str, Any]:
    path, bundle = _load_bundle(bundle_path)
    included = [
        key
        for key, value in (bundle.get("sections") or {}).items()
        if value is not None
    ]
    return {
        "success": True,
        "bundle_path": str(path),
        "artifact_name": bundle.get("artifact_name"),
        "created_at": bundle.get("created_at"),
        "connected_adb_devices": bundle.get("connected_adb_devices", 0),
        "included_sections": included,
        "notes": _derive_health_notes(bundle),
    }


def android_support_issue_draft(
    bundle_path: str = "",
    artifact_name: str = "droidpuppy_support_issue",
) -> dict[str, Any]:
    path, bundle = _load_bundle(bundle_path)
    title = _issue_title(bundle, path)
    body = _render_issue_body(path, bundle)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{artifact_name}_{path.stem}.md"
    out_path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    return {
        "success": True,
        "bundle_path": str(path),
        "title": title,
        "body": body,
        "draft_path": str(out_path),
        "created_at": _now_iso(),
    }


def android_support_share_wizard(
    bundle_path: str = "",
    recipient_hint: str = "",
    share_now: bool = False,
) -> dict[str, Any]:
    path, bundle = _load_bundle(bundle_path)
    subject = _issue_title(bundle, path)
    message = _render_share_message(path, bundle, recipient_hint=recipient_hint)
    result = None
    if share_now:
        result = android_share_text(text=message, subject=subject)
    return {
        "success": True,
        "bundle_path": str(path),
        "subject": subject,
        "message": message,
        "share_now": share_now,
        "share_result": result,
    }
