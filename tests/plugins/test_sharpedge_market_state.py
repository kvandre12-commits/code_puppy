from __future__ import annotations

import json
from datetime import datetime, timezone

from code_puppy.plugins.sharpedge_mcp_system.market_state import (
    sharpedge_market_state,
)

NOW = datetime(2026, 8, 13, 15, 0, tzinfo=timezone.utc)


def _signal(**overrides):
    payload = {
        "schema": "sharpedge.signal.v1",
        "ts": "2026-08-13T10:59:30-04:00",
        "symbol": "SPY",
        "spot": 779.1,
        "spot_source": "test_quote",
        "vwap": 777.0,
        "vs_vwap": 0.27,
        "day_chg": 0.85,
        "rng_pos": 94.0,
        "mom15": -0.03,
        "vol_mult": 0.94,
        "gamma_regime": "positive",
        "pin": 779.0,
        "call_wall": 780.0,
        "put_wall": 772.0,
        "max_pain": 772.0,
        "reference_levels": {"ORH": 777.69},
        "level_states": {
            "ORH": {
                "event_state": "accepted_above_resistance",
                "acceptance": {"state": "accepted_above"},
                "summary": "ORH exceeded",
            }
        },
        "price_authority": {
            "display_time_utc": "2026-08-13T14:59:30+00:00",
            "price_feed_lag_state": "fresh",
            "analysis_bar_lag_state": "fresh",
        },
        "trade_permission": {
            "trade_gate": "BLOCK",
            "bias": "NEUTRAL",
            "trade_permission_score": 57,
            "setup_conviction": {
                "setup_tag": "UPSIDE EXHAUSTION",
                "bias": "watch for reversal DOWN (puts)",
                "setup_gate": "WATCH",
                "reason": "upper extreme warning",
                "event_lifecycle": {
                    "status": "confirmed",
                    "persisted_without_fresh_trigger": True,
                },
                "live_trap_corroboration": {
                    "trap_score": 35,
                    "trap_bias": "NEUTRAL",
                    "trap_reason": "no failed-break trap detected",
                    "rejection_score": 35,
                    "rejection_bias": "NEUTRAL",
                    "rejection_reason": "no obvious rejection/trap",
                },
            },
            "scores": {
                "acceptance_score": {
                    "score": 78,
                    "bias": "CALLS",
                    "reason": "accepted above ORH",
                },
                "exhaustion_score": {
                    "score": 61,
                    "bias": "NEUTRAL",
                    "reason": "not exhausted",
                },
            },
        },
    }
    payload.update(overrides)
    return payload


def _write(tmp_path, payload) -> str:
    path = tmp_path / "signal.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_projects_fresh_signal_without_execution_authority(tmp_path) -> None:
    result = sharpedge_market_state(_write(tmp_path, _signal()), now=NOW)

    assert result["success"] is True
    assert result["schema"] == "sharpedge.market_state.v1"
    assert result["freshness"]["status"] == "fresh"
    assert result["freshness"]["age_seconds"] == 30.0
    assert result["microstructure"]["pin"] == 779.0
    assert result["levels"][0]["name"] == "PIN"
    assert result["levels"][0]["relation"] == "above"
    assert result["exhaustion"]["lifecycle"]["status"] == "confirmed"
    assert result["exhaustion"]["live_corroboration"]["rejection_bias"] == "NEUTRAL"
    assert result["permission"] == {
        "gate": "BLOCK",
        "bias": "NEUTRAL",
        "score": 57,
        "analytical_only": True,
        "execution_permitted": False,
    }
    assert result["unknowns"] == []


def test_marks_old_signal_stale_and_preserves_unknowns(tmp_path) -> None:
    payload = _signal(
        price_authority={},
        ts="2026-08-13T14:00:00+00:00",
        level_states={},
        trade_permission={},
    )
    result = sharpedge_market_state(
        _write(tmp_path, payload), max_age_seconds=60, now=NOW
    )

    assert result["success"] is True
    assert result["freshness"]["status"] == "stale"
    assert result["freshness"]["age_seconds"] == 3600.0
    assert "live market state is not fresh" in result["unknowns"]
    assert "level-state packets are unavailable" in result["unknowns"]
    assert "trade-permission interpretation is unavailable" in result["unknowns"]
    assert "price-authority provenance is unavailable" in result["unknowns"]


def test_rejects_wrong_contract_and_missing_market_identity(tmp_path) -> None:
    wrong = sharpedge_market_state(
        _write(tmp_path, {"schema": "something.else", "symbol": "SPY", "spot": 1}),
        now=NOW,
    )
    assert wrong["success"] is False
    assert "expected sharpedge.signal.v1" in wrong["error"]

    missing = sharpedge_market_state(
        _write(tmp_path, _signal(symbol="", spot=None)), now=NOW
    )
    assert missing["success"] is False
    assert "non-empty symbol and numeric spot" in missing["error"]


def test_fails_gracefully_for_missing_or_malformed_files(tmp_path) -> None:
    missing = sharpedge_market_state(str(tmp_path / "missing.json"), now=NOW)
    assert missing["success"] is False
    assert missing["error"] == "signal file not found"

    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    malformed = sharpedge_market_state(str(path), now=NOW)
    assert malformed["success"] is False
    assert malformed["error"].startswith("cannot read signal:")


def test_requires_positive_freshness_window(tmp_path) -> None:
    result = sharpedge_market_state(
        _write(tmp_path, _signal()), max_age_seconds=0, now=NOW
    )
    assert result == {
        "success": False,
        "schema": "sharpedge.market_state.v1",
        "error": "max_age_seconds must be positive",
    }
