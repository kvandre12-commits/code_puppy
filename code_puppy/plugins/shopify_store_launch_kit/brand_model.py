from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs")

MODEL_PRESETS: dict[str, dict[str, Any]] = {
    "operator_station": {
        "name": "Operator Station",
        "thesis": "A focused command setup for traders, builders, coders, and creators who live at a desk.",
        "hero_phrase": "Build your command station.",
        "customer": "People who want their workspace to feel controlled, sharp, and ready for pressure.",
        "product_groups": [
            {
                "name": "Surface",
                "role": "The visual anchor of the desk.",
                "products": ["desk mat", "wrist rest", "mouse pad", "desk pad"],
            },
            {
                "name": "Elevation",
                "role": "Raises screens and devices into a cleaner working posture.",
                "products": [
                    "laptop stand",
                    "monitor riser",
                    "tablet stand",
                    "phone stand",
                ],
            },
            {
                "name": "Control",
                "role": "Kills cable chaos and keeps the station tidy.",
                "products": [
                    "cable organizer",
                    "charging dock",
                    "desk tray",
                    "cord clips",
                ],
            },
            {
                "name": "Focus",
                "role": "Keeps the operator locked in.",
                "products": ["desk lamp", "timer", "notebook", "planning pad"],
            },
            {
                "name": "Carry",
                "role": "Extends the setup into everyday carry.",
                "products": ["tech pouch", "EDC organizer", "wallet", "key organizer"],
            },
        ],
        "first_drop": [
            "one premium-looking desk mat",
            "one laptop/phone stand combo",
            "two cable-control products",
            "one desk tray or EDC tray",
            "one notebook/planning pad",
            "one compact desk light",
        ],
    },
    "prep_station": {
        "name": "Prep Station",
        "thesis": "A clean kitchen workflow line for people who prep like operators, not chaos gremlins.",
        "hero_phrase": "Make the prep station sharp.",
        "customer": "Home cooks, meal-preppers, BBQ people, and butcher-adjacent practical buyers.",
        "product_groups": [
            {
                "name": "Board",
                "role": "The base surface for kitchen prep.",
                "products": ["cutting board", "prep board", "carving board"],
            },
            {
                "name": "Storage",
                "role": "Keeps tools and ingredients organized.",
                "products": ["prep containers", "knife block", "drawer organizer"],
            },
            {
                "name": "Protection",
                "role": "Makes the cook look and feel ready.",
                "products": ["apron", "cut glove", "towel", "hot pad"],
            },
            {
                "name": "BBQ Edge",
                "role": "Outdoor cook accessories that fit the sharp/prep vibe.",
                "products": [
                    "grill tools",
                    "meat thermometer",
                    "BBQ gloves",
                    "sauce brush",
                ],
            },
        ],
        "first_drop": [
            "one standout cutting board",
            "one apron",
            "one prep container set",
            "one BBQ/accessory product",
            "one safe sharpening or storage accessory",
        ],
    },
}


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _clean_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _preset(name: str) -> dict[str, Any]:
    key = (name or "operator_station").strip().lower()
    return MODEL_PRESETS.get(key, MODEL_PRESETS["operator_station"])


def _search_terms(model: dict[str, Any], extra_terms: list[str]) -> list[str]:
    terms: list[str] = []
    for group in model["product_groups"]:
        terms.extend(group["products"])
    terms.extend(extra_terms)
    return _clean_list(terms)


def _rejection_rules(model: dict[str, Any]) -> list[str]:
    base = [
        "Reject products with unclear supplier identity, shipping, or returns.",
        "Reject products whose photos feel cheap, generic, or off-brand.",
        "Reject products where margin is impossible after discounts and Shopify fees.",
        "Reject products that need heavy customer education for the first drop.",
    ]
    if model["name"] == "Prep Station":
        base.extend(
            [
                "Avoid food/consumables for launch.",
                "Avoid knives/blades unless compliance, quality, and supplier support are obvious.",
            ]
        )
    return base


def _render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# Shopify Brand Product Model: {plan['store_name']}",
        "",
        f"- Created: {plan['created_at']}",
        f"- Model: {plan['model']['name']}",
        f"- Thesis: {plan['model']['thesis']}",
        f"- Hero phrase: {plan['model']['hero_phrase']}",
        f"- Customer: {plan['model']['customer']}",
        "",
        "## Product Groups",
    ]
    for group in plan["model"]["product_groups"]:
        lines.append(f"### {group['name']}")
        lines.append(f"- Role: {group['role']}")
        lines.append(f"- Search/products: {', '.join(group['products'])}")
        lines.append("")
    lines.extend(["## First Drop", ""])
    for item in plan["model"]["first_drop"]:
        lines.append(f"- [ ] {item}")
    lines.extend(["", "## Shopify Collective Search Terms", ""])
    for term in plan["search_terms"]:
        lines.append(f"- {term}")
    lines.extend(["", "## Rejection Rules", ""])
    for rule in plan["rejection_rules"]:
        lines.append(f"- {rule}")
    lines.extend(["", "## Buying Story", ""])
    lines.append(plan["buying_story"])
    return "\n".join(lines) + "\n"


def shopify_brand_product_model_create(
    store_name: str,
    model_name: str = "operator_station",
    extra_search_terms: list[str] | None = None,
    artifact_name: str = "shopify_brand_product_model",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = (store_name or "").strip()
    if not name:
        raise ValueError("store_name is required")

    model = _preset(model_name)
    plan = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "model_key": model_name,
        "model": model,
        "search_terms": _search_terms(model, extra_search_terms or []),
        "rejection_rules": _rejection_rules(model),
        "buying_story": (
            f"Start with {model['name']} as the recognizable promise. "
            "Every first-drop product should either anchor the setup, organize the workflow, "
            "or complete the customer's station. If it does not strengthen that story, skip it."
        ),
        "approval_gates": [
            "Capture candidates first; import only after explicit operator approval.",
            "Keep imported products draft until pricing, supplier terms, and copy are reviewed.",
            "Do not approve supplier charges, payments, or publish actions autonomously.",
        ],
    }
    markdown = _render_markdown(plan)
    if dry_run:
        return {
            **plan,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{artifact_name}_{plan['created_at']}"
    json_path = OUTPUT_DIR / f"{base}.json"
    md_path = OUTPUT_DIR / f"{base}.md"
    json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return {**plan, "dry_run": False, "artifact_paths": [str(json_path), str(md_path)]}
