from __future__ import annotations

from typing import Any

from ..android_app_inventory_kit.tooling import (
    android_app_inventory_doctor,
    android_app_profile,
)


def _has_reactivate_launcher(profile: dict[str, Any]) -> bool:
    launcher = (profile.get("launcher") or {}).get("components") or []
    return any("ReactivateActivity" in component for component in launcher)


def _interaction_mode(profile: dict[str, Any]) -> str:
    if not profile.get("installed"):
        return "missing"
    if _has_reactivate_launcher(profile):
        return "reactivation_or_restore"
    if profile.get("url_view_capable") or profile.get("text_share_capable"):
        return "direct_handoff"
    if profile.get("launchable"):
        return "ui_steering"
    return "unknown"


def _readiness_score(profile: dict[str, Any]) -> int:
    if not profile.get("installed"):
        return 0
    score = 0
    if profile.get("launchable"):
        score += 40
    if profile.get("url_view_capable"):
        score += 30
    if profile.get("text_share_capable"):
        score += 20
    if profile.get("third_party"):
        score += 5
    if _has_reactivate_launcher(profile):
        score -= 35
    return max(0, min(100, score))


def _readiness_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _app_notes(profile: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if not profile.get("installed"):
        return ["App is not installed on this phone."]
    if _has_reactivate_launcher(profile):
        notes.append(
            "Launcher points to ReactivateActivity; app may be archived or partially inactive."
        )
    if profile.get("url_view_capable"):
        notes.append("Accepts URL/view-style handoffs.")
    if profile.get("text_share_capable"):
        notes.append("Accepts text share handoffs.")
    if (
        profile.get("launchable")
        and not profile.get("url_view_capable")
        and not profile.get("text_share_capable")
    ):
        notes.append("Likely requires UI steering after launch for deeper workflows.")
    if not notes:
        notes.append(
            "Little structured handoff surface detected; treat as a brittle target."
        )
    return notes


def _overall_recommendations(
    profiles: list[dict[str, Any]], business_goal: str = ""
) -> list[str]:
    recommendations: list[str] = []
    direct = [p for p in profiles if _interaction_mode(p) == "direct_handoff"]
    ui = [p for p in profiles if _interaction_mode(p) == "ui_steering"]
    missing = [p for p in profiles if _interaction_mode(p) == "missing"]
    reactivate = [
        p for p in profiles if _interaction_mode(p) == "reactivation_or_restore"
    ]

    if direct:
        recommendations.append(
            f"Start with direct handoff workflows around: {', '.join(p['package_name'] for p in direct[:5])}."
        )
    if ui:
        recommendations.append(
            f"Plan UI-guided automation for: {', '.join(p['package_name'] for p in ui[:5])}."
        )
    if reactivate:
        recommendations.append(
            f"Reactivation or reinstall may be needed before dependable automation for: {', '.join(p['package_name'] for p in reactivate[:5])}."
        )
    if missing:
        recommendations.append(
            f"Missing apps block full workflow assessment: {', '.join(p['package_name'] for p in missing[:5])}."
        )
    if business_goal.strip():
        recommendations.append(
            f"Assess every workflow step against the stated goal: {business_goal.strip()}"
        )
    if not recommendations:
        recommendations.append(
            "Start by profiling more candidate apps and testing a small cross-app workflow."
        )
    return recommendations


def _overall_band(profiles: list[dict[str, Any]]) -> str:
    if not profiles:
        return "unknown"
    scores = [_readiness_score(profile) for profile in profiles]
    avg = sum(scores) / len(scores)
    if avg >= 70:
        return "high"
    if avg >= 40:
        return "medium"
    return "low"


def android_workflow_feasibility_doctor() -> dict[str, Any]:
    inventory = android_app_inventory_doctor()
    capabilities = inventory.get("capabilities") or {}
    return {
        "success": True,
        "dependency_doctor": inventory,
        "capabilities": {
            "can_inventory_apps": bool(capabilities.get("list_packages")),
            "can_profile_apps": bool(capabilities.get("profile_apps")),
            "can_resolve_launchers": bool(capabilities.get("resolve_launcher")),
        },
        "guidance": [
            "Use android_workflow_feasibility_assess with the packages your business actually depends on.",
            "This layer identifies where direct handoff is possible versus where UI steering is likely required.",
            "High-value results come from assessing a real 3-5 app workflow stack, not random packages.",
        ],
    }


def android_workflow_feasibility_assess(
    package_names: list[str],
    business_goal: str = "",
    user: str = "0",
) -> dict[str, Any]:
    cleaned = []
    for package_name in package_names or []:
        text = str(package_name).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    if not cleaned:
        raise ValueError("package_names must contain at least one package")

    raw_profiles = [
        android_app_profile(package_name=name, user=user) for name in cleaned
    ]
    assessed_apps = []
    for profile in raw_profiles:
        score = _readiness_score(profile)
        assessed_apps.append(
            {
                "package_name": profile.get("package_name"),
                "installed": profile.get("installed"),
                "launchable": profile.get("launchable"),
                "url_view_capable": profile.get("url_view_capable"),
                "text_share_capable": profile.get("text_share_capable"),
                "interaction_mode": _interaction_mode(profile),
                "readiness_score": score,
                "readiness_band": _readiness_band(score),
                "notes": _app_notes(profile),
                "profile": profile,
            }
        )

    direct = [
        app for app in assessed_apps if app["interaction_mode"] == "direct_handoff"
    ]
    ui = [app for app in assessed_apps if app["interaction_mode"] == "ui_steering"]
    missing = [app for app in assessed_apps if app["interaction_mode"] == "missing"]
    reactivate = [
        app
        for app in assessed_apps
        if app["interaction_mode"] == "reactivation_or_restore"
    ]

    return {
        "success": True,
        "business_goal": business_goal,
        "user": str(user),
        "package_count": len(assessed_apps),
        "overall_readiness": _overall_band(raw_profiles),
        "summary": {
            "direct_handoff_candidates": [app["package_name"] for app in direct],
            "ui_steering_candidates": [app["package_name"] for app in ui],
            "reactivation_candidates": [app["package_name"] for app in reactivate],
            "missing_apps": [app["package_name"] for app in missing],
        },
        "recommendations": _overall_recommendations(
            raw_profiles, business_goal=business_goal
        ),
        "apps": assessed_apps,
    }


def android_workflow_feasibility_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "restaurant_stack",
                "description": "Assess a delivery/merchant style app stack.",
                "example_args": {
                    "package_names": [
                        "com.doordash.driverapp",
                        "com.ubercab.eats",
                        "com.brave.browser",
                    ],
                    "business_goal": "Move links, messages, and support artifacts across the daily delivery app stack.",
                },
            },
            {
                "name": "support_stack",
                "description": "Assess a browser + support + artifact sharing flow.",
                "example_args": {
                    "package_names": [
                        "com.brave.browser",
                        "com.termux",
                    ],
                    "business_goal": "Collect support evidence and move it outward quickly.",
                },
            },
        ],
        "note": "Use real packages from the phone you are standing on. That is where the friction lives.",
    }
