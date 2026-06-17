from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..android_orchestration_blueprint_kit.tooling import (
    android_orchestration_blueprint_doctor,
    android_orchestration_blueprint_plan,
)
from ..android_workflow_feasibility_kit.tooling import (
    android_workflow_feasibility_assess,
    android_workflow_feasibility_doctor,
)

OUTPUT_DIR = Path("outputs")



def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")



def _top_apps(assessment: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    apps = sorted(
        assessment.get("apps", []),
        key=lambda app: int(app.get("readiness_score") or 0),
        reverse=True,
    )
    return apps[:limit]



def _exec_summary(assessment: dict[str, Any], business_goal: str) -> dict[str, Any]:
    direct = len((assessment.get("summary") or {}).get("direct_handoff_candidates", []))
    ui = len((assessment.get("summary") or {}).get("ui_steering_candidates", []))
    reactivate = len((assessment.get("summary") or {}).get("reactivation_candidates", []))
    missing = len((assessment.get("summary") or {}).get("missing_apps", []))
    best = _top_apps(assessment, limit=3)
    return {
        "business_goal": business_goal,
        "overall_readiness": assessment.get("overall_readiness"),
        "package_count": assessment.get("package_count"),
        "direct_handoff_count": direct,
        "ui_steering_count": ui,
        "reactivation_count": reactivate,
        "missing_count": missing,
        "best_candidates": [app.get("package_name") for app in best],
    }



def _stack_overview(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "package_name": app.get("package_name"),
            "installed": app.get("installed"),
            "interaction_mode": app.get("interaction_mode"),
            "readiness_score": app.get("readiness_score"),
            "readiness_band": app.get("readiness_band"),
            "notes": app.get("notes"),
        }
        for app in assessment.get("apps", [])
    ]



def _priority_actions(assessment: dict[str, Any], blueprint: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    summary = assessment.get("summary") or {}
    direct = summary.get("direct_handoff_candidates", [])
    reactivate = summary.get("reactivation_candidates", [])
    ui = summary.get("ui_steering_candidates", [])

    if direct:
        actions.append(
            f"Pilot direct handoff first with: {', '.join(direct[:3])}."
        )
    if reactivate:
        actions.append(
            f"Repair or reinstall before promising automation for: {', '.join(reactivate[:3])}."
        )
    if ui:
        actions.append(
            f"Reserve UI-guided automation work for: {', '.join(ui[:3])}."
        )

    phases = blueprint.get("rollout_phases", [])
    if phases:
        actions.append(
            f"Use rollout phase 1 as the operating baseline: {phases[0].get('name')}"
        )

    if not actions:
        actions.append("Profile more real apps and test a narrow cross-app workflow before expanding scope.")
    return actions



def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# App Stack Report: {report.get('artifact_name')}",
        "",
        "## Executive Summary",
        f"- Goal: {report.get('business_goal') or 'No business goal provided.'}",
        f"- Overall readiness: {((report.get('executive_summary') or {}).get('overall_readiness'))}",
        f"- Packages assessed: {((report.get('executive_summary') or {}).get('package_count'))}",
        f"- Direct handoff candidates: {((report.get('executive_summary') or {}).get('direct_handoff_count'))}",
        f"- UI steering candidates: {((report.get('executive_summary') or {}).get('ui_steering_count'))}",
        f"- Reactivation-bound apps: {((report.get('executive_summary') or {}).get('reactivation_count'))}",
        "",
        "## Best Candidates",
    ]
    for package_name in ((report.get("executive_summary") or {}).get("best_candidates") or []):
        lines.append(f"- `{package_name}`")
    lines.extend(["", "## Priority Actions"])
    for action in report.get("priority_actions", []):
        lines.append(f"- {action}")
    lines.extend(["", "## Stack Overview"])
    for app in report.get("stack_overview", []):
        lines.append(
            f"- `{app.get('package_name')}` — mode={app.get('interaction_mode')}, readiness={app.get('readiness_band')} ({app.get('readiness_score')})"
        )
        for note in app.get("notes", [])[:2]:
            lines.append(f"  - {note}")
    lines.extend(["", "## Recommendations"])
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    lines.extend(["", "## Blueprint Rollout Phases"])
    for phase in (report.get("blueprint") or {}).get("rollout_phases", []):
        lines.append(
            f"- Phase {phase.get('phase')}: **{phase.get('name')}** — {phase.get('focus')}"
        )
    return "\n".join(lines) + "\n"



def android_app_stack_report_doctor() -> dict[str, Any]:
    feasibility = android_workflow_feasibility_doctor()
    blueprint = android_orchestration_blueprint_doctor()
    return {
        "success": True,
        "dependency_doctors": {
            "feasibility": feasibility,
            "blueprint": blueprint,
        },
        "guidance": [
            "Use android_app_stack_report_generate with the actual apps a team depends on.",
            "This layer creates a business-readable summary from feasibility and blueprint analysis.",
            "Use dry_run first if you only want to inspect the report structure.",
        ],
    }



def android_app_stack_report_generate(
    package_names: list[str],
    business_goal: str = "",
    artifact_name: str = "droidpuppy_app_stack_report",
    dry_run: bool = True,
    user: str = "0",
) -> dict[str, Any]:
    assessment = android_workflow_feasibility_assess(
        package_names=package_names,
        business_goal=business_goal,
        user=user,
    )
    blueprint = android_orchestration_blueprint_plan(
        package_names=package_names,
        business_goal=business_goal,
        artifact_name=f"{artifact_name}_blueprint",
        dry_run=True,
        user=user,
    )

    created_at = _timestamp()
    report = {
        "success": True,
        "artifact_name": artifact_name,
        "created_at": created_at,
        "business_goal": business_goal,
        "package_names": package_names,
        "executive_summary": _exec_summary(assessment, business_goal=business_goal),
        "priority_actions": _priority_actions(assessment, blueprint),
        "stack_overview": _stack_overview(assessment),
        "recommendations": assessment.get("recommendations", []),
        "assessment": assessment,
        "blueprint": blueprint,
    }

    json_path = OUTPUT_DIR / f"{artifact_name}_{created_at}.json"
    md_path = OUTPUT_DIR / f"{artifact_name}_{created_at}.md"

    if dry_run:
        return {
            **report,
            "dry_run": True,
            "expected_artifacts": [str(json_path), str(md_path)],
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return {
        **report,
        "dry_run": False,
        "artifact_paths": [str(json_path), str(md_path)],
    }



def android_app_stack_report_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "delivery_stack_report",
                "description": "Create a readable report for a delivery-style app stack.",
                "example_args": {
                    "package_names": [
                        "com.brave.browser",
                        "com.doordash.driverapp",
                        "com.ubercab.eats",
                    ],
                    "business_goal": "Move links, messages, and support artifacts across a delivery-style app stack.",
                    "dry_run": True,
                },
            },
            {
                "name": "support_stack_report",
                "description": "Create a readable support-oriented report for a browser + termux stack.",
                "example_args": {
                    "package_names": [
                        "com.brave.browser",
                        "com.termux",
                    ],
                    "business_goal": "Collect and move support evidence outward quickly.",
                    "dry_run": True,
                },
            },
        ],
        "note": "This report is for people, not just tools. It should be readable by the team living inside the app stack.",
    }
