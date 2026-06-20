from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..android_workflow_feasibility_kit.tooling import (
    android_workflow_feasibility_assess,
    android_workflow_feasibility_doctor,
)

OUTPUT_DIR = Path("outputs")


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _find_apps(assessment: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    return [
        app for app in assessment.get("apps", []) if app.get("interaction_mode") == mode
    ]


def _preferred_entry_app(assessment: dict[str, Any]) -> str | None:
    apps = sorted(
        assessment.get("apps", []),
        key=lambda app: int(app.get("readiness_score") or 0),
        reverse=True,
    )
    for app in apps:
        if app.get("interaction_mode") in {"direct_handoff", "ui_steering"}:
            return app.get("package_name")
    return apps[0].get("package_name") if apps else None


def _pilot_workflows(
    assessment: dict[str, Any], business_goal: str
) -> list[dict[str, Any]]:
    direct = _find_apps(assessment, "direct_handoff")
    ui = _find_apps(assessment, "ui_steering")
    reactivate = _find_apps(assessment, "reactivation_or_restore")

    pilots: list[dict[str, Any]] = []

    for app in direct[:2]:
        package = app.get("package_name")
        pilots.append(
            {
                "name": f"direct_handoff_{package}",
                "summary": f"Use explicit URL/text handoff with {package} as an early low-friction workflow.",
                "why": "This app exposes structured handoff surfaces and should be easier to integrate first.",
                "recommended_tools": [
                    "android_handoff_url",
                    "android_handoff_text",
                    "android_intent_send",
                ],
            }
        )

    for app in ui[:2]:
        package = app.get("package_name")
        pilots.append(
            {
                "name": f"ui_guided_{package}",
                "summary": f"Launch {package} and complete deeper steps with UI inspection and input tools.",
                "why": "This app appears launchable but lacks strong structured handoff surfaces.",
                "recommended_tools": [
                    "android_intent_send",
                    "android_ui_dump_hierarchy",
                    "android_ui_dump_find",
                    "android_ui_tap_match",
                ],
            }
        )

    if reactivate:
        pilots.append(
            {
                "name": "reactivation_repair_lane",
                "summary": "Repair or reinstall reactivation-bound apps before deeper automation work.",
                "why": "Archived or reactivation-only launchers create brittle workflows.",
                "recommended_tools": [
                    "android_app_profile",
                    "android_support_bundle_collect",
                    "android_support_share_wizard",
                ],
            }
        )

    pilots.append(
        {
            "name": "support_bundle_outbound",
            "summary": "Always keep a support bundle path available for broken workflows and weird app state.",
            "why": "Reliable support discipline makes experimentation safer and more business-usable.",
            "recommended_tools": [
                "android_support_bundle_collect",
                "android_support_issue_draft",
                "android_support_share_wizard",
            ],
        }
    )

    if business_goal.strip():
        pilots.append(
            {
                "name": "goal_validation_loop",
                "summary": f"Test each pilot against the stated goal: {business_goal.strip()}",
                "why": "The point is business friction reduction, not random automation wins.",
                "recommended_tools": [
                    "android_app_workflow_run",
                    "android_workflow_feasibility_assess",
                ],
            }
        )

    return pilots


def _risk_register(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for app in assessment.get("apps", []):
        mode = app.get("interaction_mode")
        package = app.get("package_name")
        if mode == "reactivation_or_restore":
            risks.append(
                {
                    "package_name": package,
                    "severity": "high",
                    "risk": "App may be archived, reactivation-bound, or not in a healthy launch state.",
                }
            )
        elif mode == "ui_steering":
            risks.append(
                {
                    "package_name": package,
                    "severity": "medium",
                    "risk": "Workflow may rely on visible UI steering instead of structured handoffs.",
                }
            )
        elif mode == "missing":
            risks.append(
                {
                    "package_name": package,
                    "severity": "high",
                    "risk": "App is not installed on the current phone.",
                }
            )
    if not risks:
        risks.append(
            {
                "package_name": "stack",
                "severity": "low",
                "risk": "No major structural blockers detected from package profiling alone; live workflow testing still matters.",
            }
        )
    return risks


def _rollout_phases(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    ui = _find_apps(assessment, "ui_steering")
    reactivate = _find_apps(assessment, "reactivation_or_restore")

    phases: list[dict[str, Any]] = []

    def add_phase(name: str, focus: str, recommended_tools: list[str]) -> None:
        phases.append(
            {
                "phase": len(phases) + 1,
                "name": name,
                "focus": focus,
                "recommended_tools": recommended_tools,
            }
        )

    add_phase(
        "stack_audit",
        "Confirm package reality, launch paths, and handoff surfaces.",
        [
            "android_app_inventory_list",
            "android_app_profile",
            "android_workflow_feasibility_assess",
        ],
    )
    add_phase(
        "pilot_direct_handoffs",
        "Start with the cleanest direct handoff apps first.",
        [
            "android_handoff_url",
            "android_handoff_text",
            "android_intent_send",
        ],
    )

    if ui:
        add_phase(
            "ui_guided_expansion",
            "Expand into apps that require launch + UI steering.",
            [
                "android_ui_dump_hierarchy",
                "android_ui_dump_find",
                "android_ui_tap_match",
                "android_app_workflow_run",
            ],
        )
    if reactivate:
        add_phase(
            "repair_or_reinstall_lane",
            "Stabilize problematic apps before promising automation around them.",
            [
                "android_app_profile",
                "android_support_bundle_collect",
                "android_support_share_wizard",
            ],
        )

    add_phase(
        "support_and_recovery",
        "Keep diagnostics and support sharing ready for every production workflow.",
        [
            "android_support_bundle_collect",
            "android_support_issue_draft",
            "android_support_share_wizard",
        ],
    )
    return phases


def _recommended_tools(assessment: dict[str, Any]) -> list[str]:
    tools = [
        "android_workflow_feasibility_assess",
        "android_app_profile",
        "android_app_workflow_run",
        "android_support_bundle_collect",
        "android_support_share_wizard",
    ]
    if _find_apps(assessment, "direct_handoff"):
        tools.extend(
            ["android_handoff_url", "android_handoff_text", "android_intent_send"]
        )
    if _find_apps(assessment, "ui_steering"):
        tools.extend(
            [
                "android_ui_dump_hierarchy",
                "android_ui_dump_find",
                "android_ui_tap_match",
            ]
        )
    deduped: list[str] = []
    for tool in tools:
        if tool not in deduped:
            deduped.append(tool)
    return deduped


def _render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# Orchestration Blueprint: {plan.get('artifact_name', 'droidpuppy_blueprint')}",
        "",
        "## Goal",
        plan.get("business_goal") or "No business goal provided.",
        "",
        "## Overall Readiness",
        f"- {plan.get('overall_readiness')}",
        "",
        "## Execution Model",
        f"- Preferred entry app: `{(plan.get('execution_model') or {}).get('preferred_entry_app')}`",
        f"- Primary style: {(plan.get('execution_model') or {}).get('primary_style')}",
        f"- Support posture: {(plan.get('execution_model') or {}).get('support_posture')}",
        "",
        "## Rollout Phases",
    ]
    for phase in plan.get("rollout_phases", []):
        lines.append(
            f"- Phase {phase.get('phase')}: **{phase.get('name')}** — {phase.get('focus')}"
        )
    lines.extend(["", "## Pilot Workflows"])
    for pilot in plan.get("pilot_workflows", []):
        lines.append(f"- **{pilot.get('name')}** — {pilot.get('summary')}")
    lines.extend(["", "## Risks"])
    for risk in plan.get("risk_register", []):
        lines.append(
            f"- **{risk.get('severity')}** `{risk.get('package_name')}` — {risk.get('risk')}"
        )
    lines.extend(["", "## Recommended Tools"])
    for tool in plan.get("recommended_tools", []):
        lines.append(f"- `{tool}`")
    return "\n".join(lines) + "\n"


def android_orchestration_blueprint_doctor() -> dict[str, Any]:
    feasibility = android_workflow_feasibility_doctor()
    return {
        "success": True,
        "dependency_doctor": feasibility,
        "guidance": [
            "Use android_orchestration_blueprint_plan with a real set of business apps.",
            "This layer turns feasibility into a rollout blueprint instead of a raw technical report.",
            "Use dry_run first if you only want to inspect the plan without writing artifacts.",
        ],
    }


def android_orchestration_blueprint_plan(
    package_names: list[str],
    business_goal: str = "",
    artifact_name: str = "droidpuppy_orchestration_blueprint",
    dry_run: bool = True,
    user: str = "0",
) -> dict[str, Any]:
    assessment = android_workflow_feasibility_assess(
        package_names=package_names,
        business_goal=business_goal,
        user=user,
    )

    plan = {
        "success": True,
        "artifact_name": artifact_name,
        "created_at": _timestamp(),
        "business_goal": business_goal,
        "package_names": package_names,
        "overall_readiness": assessment.get("overall_readiness"),
        "execution_model": {
            "preferred_entry_app": _preferred_entry_app(assessment),
            "primary_style": "direct_handoff_first_with_ui_fallback",
            "support_posture": "always_collect_and_share_support_bundle_when_workflows_break",
        },
        "summary": assessment.get("summary"),
        "rollout_phases": _rollout_phases(assessment),
        "pilot_workflows": _pilot_workflows(assessment, business_goal=business_goal),
        "risk_register": _risk_register(assessment),
        "recommended_tools": _recommended_tools(assessment),
        "assessment": assessment,
    }

    json_path = OUTPUT_DIR / f"{artifact_name}_{plan['created_at']}.json"
    md_path = OUTPUT_DIR / f"{artifact_name}_{plan['created_at']}.md"

    if dry_run:
        return {
            **plan,
            "dry_run": True,
            "expected_artifacts": [str(json_path), str(md_path)],
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(plan), encoding="utf-8")
    return {
        **plan,
        "dry_run": False,
        "artifact_paths": [str(json_path), str(md_path)],
    }


def android_orchestration_blueprint_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "delivery_stack_blueprint",
                "description": "Plan an orchestration rollout for a delivery-style app stack.",
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
                "name": "support_stack_blueprint",
                "description": "Plan a support-oriented browser and artifact flow.",
                "example_args": {
                    "package_names": [
                        "com.brave.browser",
                        "com.termux",
                    ],
                    "business_goal": "Collect, package, and share support evidence quickly.",
                    "dry_run": True,
                },
            },
        ],
        "note": "This layer turns package reality into a rollout plan. That is how messy app stacks become workable.",
    }
