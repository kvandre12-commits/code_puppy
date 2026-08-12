from __future__ import annotations

import json

from code_puppy.plugins.shopify_store_launch_kit.brand_model import (
    shopify_brand_product_model_create,
)
from code_puppy.plugins.shopify_store_launch_kit.product_story import (
    shopify_collective_search_batch_create,
    shopify_first_ten_story_create,
    shopify_product_hunt_run,
    shopify_product_story_fit_report,
)
from code_puppy.plugins.shopify_store_launch_kit.winner_board import (
    shopify_winner_board_build,
)
from code_puppy.plugins.shopify_store_launch_kit.tooling import (
    shopify_admin_navigation_helper,
    shopify_import_prompt_create,
    shopify_product_curation_capture,
    shopify_store_launch_kit_doctor,
    shopify_store_launch_plan_create,
    shopify_store_launch_template,
)


def test_doctor_lists_tools_and_approval_gates() -> None:
    result = shopify_store_launch_kit_doctor()

    assert result["success"] is True
    assert "shopify_product_curation_capture" in result["tools"]
    assert "shopify_brand_product_model_create" in result["tools"]
    assert "shopify_first_ten_story_create" in result["tools"]
    assert "shopify_product_story_fit_report" in result["tools"]
    assert "shopify_product_hunt_run" in result["tools"]
    assert "shopify_winner_board_build" in result["tools"]
    assert any("Do not import" in gate for gate in result["approval_gates"])


def test_template_defaults_to_desk_operator_lane() -> None:
    result = shopify_store_launch_template()

    assert result["success"] is True
    assert result["template"]["store_name"] == "SharpEdge"
    assert "desk mats" in result["lane"]["product_types"]


def test_launch_plan_dry_run_does_not_write(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = shopify_store_launch_plan_create(store_name="SharpEdge", dry_run=True)

    assert result["dry_run"] is True
    assert result["primary_lane"]["name"] == "Desk / operator gear"
    assert not (tmp_path / "outputs").exists()


def test_launch_plan_writes_json_and_markdown(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = shopify_store_launch_plan_create(
        store_name="SharpEdge",
        artifact_name="sharpedge_launch",
        dry_run=False,
    )

    paths = result["artifact_paths"]
    assert len(paths) == 2
    json_path = tmp_path / paths[0]
    md_path = tmp_path / paths[1]
    assert json_path.exists()
    assert md_path.exists()
    assert (
        json.loads(json_path.read_text(encoding="utf-8"))["store_name"] == "SharpEdge"
    )
    assert "# Shopify Launch Plan" in md_path.read_text(encoding="utf-8")


def test_product_curation_scores_and_flags_candidates() -> None:
    result = shopify_product_curation_capture(
        store_name="SharpEdge",
        candidates=[
            {
                "title": "Executive Desk Mat and Cable Organizer",
                "supplier": "Desk Co",
                "price": "$39.00",
                "why_it_fits": "desk mat for operators",
            },
            {
                "title": "Mystery Knife Blade Set",
                "supplier": "",
                "price": "",
            },
        ],
        dry_run=True,
    )

    ranked = result["ranked_candidates"]
    assert ranked[0]["title"] == "Executive Desk Mat and Cable Organizer"
    assert ranked[0]["recommendation"] == "strong_candidate"
    assert "sharp_tool_compliance_review" in ranked[1]["risk_flags"]
    assert ranked[1]["approval_required_before_import"] is True


def test_import_prompt_requires_operator_confirmation() -> None:
    result = shopify_import_prompt_create(
        candidate={"title": "Desk Mat", "supplier": "Desk Co", "price": "$39"},
        dry_run=True,
    )

    assert result["operator_confirmation_required"] is True
    assert result["write_action"] == "product_import_review_only"
    assert any("draft" in item for item in result["verification_checklist"])


def test_brand_product_model_turns_products_into_story() -> None:
    result = shopify_brand_product_model_create(
        store_name="SharpEdge",
        model_name="operator_station",
        extra_search_terms=["desk shelf"],
        dry_run=True,
    )

    assert result["success"] is True
    assert result["model"]["name"] == "Operator Station"
    assert "desk mat" in result["search_terms"]
    assert "desk shelf" in result["search_terms"]
    assert "Every first-drop product" in result["buying_story"]


def test_brand_product_model_writes_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = shopify_brand_product_model_create(
        store_name="SharpEdge",
        model_name="prep_station",
        artifact_name="sharpedge_product_model",
        dry_run=False,
    )

    paths = result["artifact_paths"]
    assert len(paths) == 2
    md_path = tmp_path / paths[1]
    assert md_path.exists()
    markdown = md_path.read_text(encoding="utf-8")
    assert "# Shopify Brand Product Model" in markdown
    assert "Prep Station" in markdown


def test_first_ten_story_creates_slots_and_sequence() -> None:
    result = shopify_first_ten_story_create(
        store_name="SharpEdge",
        model_name="operator_station",
        dry_run=True,
    )

    assert result["success"] is True
    assert result["theme_sentence"] == (
        "SharpEdge sells products that build a complete Operator Station."
    )
    assert len(result["first_ten_sequence"]) == 10
    assert result["slots"][0]["slot"] == "Surface Anchor"


def test_collective_search_batch_groups_terms_by_story_slot() -> None:
    result = shopify_collective_search_batch_create(
        store_slug="sharpedge-6969",
        model_name="operator_station",
    )

    assert result["success"] is True
    first = result["searches"][0]
    assert first["slot"] == "Surface Anchor"
    assert first["term"] == "desk mat"
    assert "q=desk+mat" in first["url_hint"]


def test_product_story_fit_report_shortlists_and_finds_gaps() -> None:
    result = shopify_product_story_fit_report(
        store_name="SharpEdge",
        candidates=[
            {
                "title": "Premium Desk Mat",
                "supplier": "Desk Co",
                "price": "$39",
                "why_it_fits": "Anchors the command station surface.",
            },
            {
                "title": "Mystery Random Box",
                "supplier": "",
                "price": "",
            },
        ],
        dry_run=True,
    )

    assert result["operator_confirmation_required_before_import"] is True
    assert result["shortlist"][0]["title"] == "Premium Desk Mat"
    assert result["shortlist"][0]["best_fit"]["slot"] == "Surface Anchor"
    assert result["rejects"][0]["title"] == "Mystery Random Box"
    assert any(gap["missing_count"] > 0 for gap in result["gaps"])


def test_first_ten_story_writes_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = shopify_first_ten_story_create(
        store_name="SharpEdge",
        artifact_name="sharpedge_first_ten",
        dry_run=False,
    )

    paths = result["artifact_paths"]
    assert len(paths) == 2
    markdown = (tmp_path / paths[1]).read_text(encoding="utf-8")
    assert "# First Ten Product Story" in markdown
    assert "Surface Anchor" in markdown


def test_product_hunt_run_picks_next_missing_search() -> None:
    result = shopify_product_hunt_run(
        store_name="SharpEdge",
        store_slug="sharpedge-6969",
        candidates=[],
        dry_run=True,
    )

    assert result["success"] is True
    assert result["next_search"]["slot"] == "Surface Anchor"
    assert result["next_search"]["term"] == "desk mat"
    assert result["capture_template"]["example"]["why_it_fits"].startswith(
        "Fits Surface Anchor"
    )
    assert result["fit_report"]["gaps"][0]["missing_count"] == 1


def test_product_hunt_run_writes_audit_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = shopify_product_hunt_run(
        store_name="SharpEdge",
        store_slug="sharpedge-6969",
        candidates=[
            {
                "title": "Premium Desk Mat",
                "supplier": "Desk Co",
                "price": "$39",
                "why_it_fits": "Surface anchor for the station.",
            }
        ],
        artifact_name="sharpedge_hunt_run",
        dry_run=False,
    )

    paths = result["artifact_paths"]
    assert len(paths) == 2
    markdown = (tmp_path / paths[1]).read_text(encoding="utf-8")
    assert "# Shopify Product Hunt Run" in markdown
    assert "Device Elevation" in markdown


def test_winner_board_selects_winners_and_copy() -> None:
    result = shopify_winner_board_build(
        store_name="SharpEdge",
        candidates=[
            {
                "title": "Premium Desk Mat",
                "supplier": "Desk Co",
                "price": "$39",
                "why_it_fits": "Surface anchor for the operator station.",
            },
            {
                "title": "Aluminum Laptop Stand",
                "supplier": "Stand Co",
                "price": "$49",
                "why_it_fits": "Raises devices for a cleaner station.",
            },
            {
                "title": "Mystery Random Box",
                "supplier": "",
                "price": "",
            },
        ],
        dry_run=True,
    )

    assert result["success"] is True
    assert result["winners_by_slot"]["surface_anchor"][0]["title"] == "Premium Desk Mat"
    assert (
        result["winners_by_slot"]["device_elevation"][0]["title"]
        == "Aluminum Laptop Stand"
    )
    assert result["launch_ready"] is False
    assert (
        result["theme_copy"]["homepage_hero"]["headline"]
        == "Build your command station."
    )
    assert result["unselected_candidates"][0]["title"] == "Mystery Random Box"


def test_winner_board_writes_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = shopify_winner_board_build(
        store_name="SharpEdge",
        candidates=[
            {
                "title": "Premium Desk Mat",
                "supplier": "Desk Co",
                "price": "$39",
                "why_it_fits": "Surface anchor for the operator station.",
            }
        ],
        artifact_name="sharpedge_winner_board",
        dry_run=False,
    )

    paths = result["artifact_paths"]
    assert len(paths) == 2
    markdown = (tmp_path / paths[1]).read_text(encoding="utf-8")
    assert "# Shopify Winner Board" in markdown
    assert "Premium Desk Mat" in markdown
    assert "Homepage Copy" in markdown


def test_navigation_helper_builds_store_urls() -> None:
    result = shopify_admin_navigation_helper(
        store_slug="sharpedge-6969",
        target="products",
    )

    assert result["success"] is True
    assert result["url"] == "https://admin.shopify.com/store/sharpedge-6969/products"
    assert "collective_discovery" in result["known_targets"]
