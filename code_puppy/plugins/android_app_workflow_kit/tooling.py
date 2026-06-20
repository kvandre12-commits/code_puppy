from __future__ import annotations

from pathlib import Path
from typing import Any

from ..android_handoff_kit.tooling import (
    android_handoff_doctor,
    android_handoff_file,
    android_handoff_text,
    android_handoff_url,
)
from ..android_intent_kit.tooling import android_intent_doctor, android_intent_send
from ..android_support_bundle_kit.tooling import android_support_bundle_collect
from ..android_support_share_wizard.tooling import (
    android_support_issue_draft,
    android_support_share_wizard,
)

OUTPUT_DIR = Path("outputs")
DEFAULT_REPO_URL = "https://github.com/kvandre12-commits/DroidPuppy"

WORKFLOWS = {
    "open_repo_in_brave": "Open the DroidPuppy repo in Brave using the handoff layer.",
    "share_repo_link": "Share the DroidPuppy repo link outward through Android.",
    "latest_screenshot_share": "Find the newest PNG in outputs/ and share it through Android.",
    "support_bundle_collect_and_share": "Collect a support bundle and immediately prepare/share a summary.",
    "support_issue_draft_and_share": "Draft a support issue from the newest bundle and share the draft text.",
    "open_wifi_and_wireless_debugging": "Walk the user into Wi-Fi and wireless debugging settings through sequential intents.",
}


def _latest_matching(pattern: str) -> Path | None:
    if not OUTPUT_DIR.exists():
        return None
    matches = [path for path in OUTPUT_DIR.glob(pattern) if path.is_file()]
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def android_app_workflow_doctor() -> dict[str, Any]:
    intent = android_intent_doctor()
    handoff = android_handoff_doctor()
    latest_png = _latest_matching("*.png")
    latest_bundle = _latest_matching("*support_bundle*.json")
    latest_issue = _latest_matching("*support_issue*.md")
    return {
        "success": True,
        "workflow_count": len(WORKFLOWS),
        "dependencies": {
            "intent": intent,
            "handoff": handoff,
        },
        "artifacts": {
            "latest_png": str(latest_png) if latest_png else None,
            "latest_support_bundle": str(latest_bundle) if latest_bundle else None,
            "latest_support_issue": str(latest_issue) if latest_issue else None,
        },
        "guidance": [
            "Use android_app_workflow_list to see named cross-app workflows.",
            "Use dry_run=True first when exploring a new workflow.",
            "The support workflows show the clearest example of DroidPuppy coordinating artifacts and apps together.",
        ],
    }


def android_app_workflow_list() -> dict[str, Any]:
    return {
        "success": True,
        "workflow_count": len(WORKFLOWS),
        "workflows": [
            {"name": name, "description": description}
            for name, description in WORKFLOWS.items()
        ],
        "examples": [
            "android_app_workflow_run(name='open_repo_in_brave', dry_run=True)",
            "android_app_workflow_run(name='share_repo_link', dry_run=True)",
            "android_app_workflow_run(name='support_bundle_collect_and_share', dry_run=True)",
            "android_app_workflow_run(name='latest_screenshot_share', dry_run=True)",
        ],
    }


def _workflow_open_repo_in_brave(repo_url: str, dry_run: bool) -> dict[str, Any]:
    return {
        "workflow": "open_repo_in_brave",
        "steps": [
            {
                "name": "handoff_repo_url",
                "result": android_handoff_url(
                    url=repo_url,
                    package_name="com.brave.browser",
                    dry_run=dry_run,
                ),
            }
        ],
    }


def _workflow_share_repo_link(repo_url: str, dry_run: bool) -> dict[str, Any]:
    return {
        "workflow": "share_repo_link",
        "steps": [
            {
                "name": "share_repo_text",
                "result": android_handoff_text(
                    text=repo_url,
                    subject="DroidPuppy repo",
                    dry_run=dry_run,
                ),
            }
        ],
    }


def _workflow_latest_screenshot_share(dry_run: bool) -> dict[str, Any]:
    latest_png = _latest_matching("*.png")
    if not latest_png:
        raise FileNotFoundError("No PNG artifacts were found in outputs/")
    return {
        "workflow": "latest_screenshot_share",
        "steps": [
            {
                "name": "share_latest_png",
                "result": android_handoff_file(
                    file_path=str(latest_png),
                    send=True,
                    chooser=True,
                    dry_run=dry_run,
                ),
            }
        ],
    }


def _workflow_support_bundle_collect_and_share(
    artifact_name: str,
    recipient_hint: str,
    dry_run: bool,
) -> dict[str, Any]:
    collect_result = android_support_bundle_collect(
        artifact_name=artifact_name,
        dry_run=dry_run,
        include_screenshot=True,
        include_logcat=True,
        include_dumpsys=True,
    )

    if dry_run:
        share_result = {
            "success": True,
            "dry_run": True,
            "message": "Would share the collected support bundle summary after collection.",
        }
    else:
        bundle_path = collect_result.get("bundle_json_path", "")
        share_result = android_support_share_wizard(
            bundle_path=bundle_path,
            recipient_hint=recipient_hint,
            share_now=True,
        )

    return {
        "workflow": "support_bundle_collect_and_share",
        "steps": [
            {"name": "collect_support_bundle", "result": collect_result},
            {"name": "share_bundle_summary", "result": share_result},
        ],
    }


def _workflow_support_issue_draft_and_share(dry_run: bool) -> dict[str, Any]:
    draft_result = android_support_issue_draft()
    share_result = android_handoff_text(
        text=draft_result.get("body", ""),
        subject=draft_result.get("title", "DroidPuppy support issue"),
        dry_run=dry_run,
    )
    return {
        "workflow": "support_issue_draft_and_share",
        "steps": [
            {"name": "draft_support_issue", "result": draft_result},
            {"name": "share_issue_text", "result": share_result},
        ],
    }


def _workflow_open_wifi_and_wireless_debugging(dry_run: bool) -> dict[str, Any]:
    wifi = android_intent_send(
        action="android.settings.WIFI_SETTINGS",
        dry_run=dry_run,
    )
    wireless = android_intent_send(
        action="android.settings.WIRELESS_SETTINGS",
        dry_run=dry_run,
    )
    return {
        "workflow": "open_wifi_and_wireless_debugging",
        "steps": [
            {"name": "open_wifi_settings", "result": wifi},
            {"name": "open_wireless_settings", "result": wireless},
        ],
        "note": "On a live run, Android will show the last launched settings screen. This still gives the user a guided path.",
    }


def android_app_workflow_run(
    name: str,
    dry_run: bool = True,
    repo_url: str = DEFAULT_REPO_URL,
    artifact_name: str = "droidpuppy_workflow_support_bundle",
    recipient_hint: str = "",
) -> dict[str, Any]:
    workflow = (name or "").strip().lower()
    if workflow not in WORKFLOWS:
        raise ValueError(
            f"Unknown workflow '{name}'. Use android_app_workflow_list to see options."
        )

    if workflow == "open_repo_in_brave":
        body = _workflow_open_repo_in_brave(repo_url=repo_url, dry_run=dry_run)
    elif workflow == "share_repo_link":
        body = _workflow_share_repo_link(repo_url=repo_url, dry_run=dry_run)
    elif workflow == "latest_screenshot_share":
        body = _workflow_latest_screenshot_share(dry_run=dry_run)
    elif workflow == "support_bundle_collect_and_share":
        body = _workflow_support_bundle_collect_and_share(
            artifact_name=artifact_name,
            recipient_hint=recipient_hint,
            dry_run=dry_run,
        )
    elif workflow == "support_issue_draft_and_share":
        body = _workflow_support_issue_draft_and_share(dry_run=dry_run)
    elif workflow == "open_wifi_and_wireless_debugging":
        body = _workflow_open_wifi_and_wireless_debugging(dry_run=dry_run)
    else:
        raise RuntimeError(f"Workflow '{name}' is not implemented")

    return {
        "success": True,
        "name": workflow,
        "dry_run": dry_run,
        **body,
    }
