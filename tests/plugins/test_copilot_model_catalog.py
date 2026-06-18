"""Tests for Copilot model catalogue pruning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from code_puppy.plugins.copilot_auth import model_catalog, utils


@dataclass
class FakeResponse:
    status_code: int
    payload: dict[str, Any]
    text: str = ""

    def json(self) -> dict[str, Any]:
        return self.payload


def _unsupported_response() -> FakeResponse:
    return FakeResponse(
        400,
        {"error": {"code": "model_not_supported", "message": "nope"}},
        "model_not_supported",
    )


def test_extract_chat_candidate_ids_filters_obvious_non_chat_models():
    entries = [
        {"id": "gpt-4o", "capabilities": {"type": "chat"}},
        {"id": "text-embedding-3-small"},
        {"id": "image-maker", "capabilities": {"type": "image"}},
        {"id": "disabled-chat", "enabled": False},
        {"name": "claude-sonnet-4", "supported_endpoints": ["chat/completions"]},
        "gpt-4o",
    ]

    assert model_catalog._extract_chat_candidate_ids(entries) == [
        "gpt-4o",
        "claude-sonnet-4",
    ]


def test_filter_chat_supported_models_drops_only_model_not_supported(monkeypatch):
    def fake_post(url, json, headers, timeout):
        if json["model"] == "bad-model":
            return _unsupported_response()
        if json["model"] == "parameter-weird-model":
            return FakeResponse(
                400,
                {"error": {"code": "unsupported_parameter", "message": "max_tokens"}},
                "unsupported_parameter",
            )
        return FakeResponse(200, {"choices": []})

    monkeypatch.setattr(model_catalog.requests, "post", fake_post)

    assert model_catalog.filter_chat_supported_models(
        "session-token",
        "https://api.githubcopilot.com",
        ["good-model", "bad-model", "parameter-weird-model"],
    ) == ["good-model", "parameter-weird-model"]


def test_fetch_supported_copilot_models_prunes_catalogue_with_probe(monkeypatch):
    def fake_get(url, headers, timeout):
        return FakeResponse(
            200,
            {
                "data": [
                    {"id": "gpt-4o", "capabilities": {"type": "chat"}},
                    {"id": "text-embedding-3-small"},
                    {"id": "catalogue-only-model"},
                ]
            },
        )

    def fake_post(url, json, headers, timeout):
        if json["model"] == "catalogue-only-model":
            return _unsupported_response()
        return FakeResponse(200, {"choices": []})

    monkeypatch.setattr(model_catalog.requests, "get", fake_get)
    monkeypatch.setattr(model_catalog.requests, "post", fake_post)

    assert model_catalog.fetch_supported_copilot_models(
        "session-token",
        "github.com",
        "https://api.githubcopilot.com",
    ) == ["gpt-4o"]


def test_add_models_to_config_prunes_stale_models_for_same_host(monkeypatch):
    saved: dict[str, Any] = {}

    monkeypatch.setattr(
        utils,
        "load_copilot_models",
        lambda: {
            "copilot-old-bad": {
                "oauth_source": "copilot-auth-plugin",
                "copilot_host": "github.com",
            },
            "copilot-enterprise-old": {
                "oauth_source": "copilot-auth-plugin",
                "copilot_host": "ghe.example.com",
            },
            "custom-model": {"type": "custom_openai"},
        },
    )
    monkeypatch.setattr(utils, "get_api_endpoint_for_host", lambda host: "https://api")

    def fake_save(models):
        saved.update(models)
        return True

    monkeypatch.setattr(utils, "save_copilot_models", fake_save)

    assert utils.add_models_to_config(["gpt-4o"], "github.com") is True
    assert "copilot-old-bad" not in saved
    assert "copilot-gpt-4o" in saved
    assert "copilot-enterprise-old" in saved
    assert "custom-model" in saved


def test_fetch_supported_copilot_models_validates_default_fallback(monkeypatch):
    monkeypatch.setattr(model_catalog, "DEFAULT_COPILOT_MODELS", ["good", "bad"])

    def fake_get(url, headers, timeout):
        return FakeResponse(503, {}, "sad trombone")

    def fake_post(url, json, headers, timeout):
        if json["model"] == "bad":
            return _unsupported_response()
        return FakeResponse(200, {"choices": []})

    monkeypatch.setattr(model_catalog.requests, "get", fake_get)
    monkeypatch.setattr(model_catalog.requests, "post", fake_post)

    assert model_catalog.fetch_supported_copilot_models(
        "session-token",
        "github.com",
        "https://api.githubcopilot.com",
    ) == ["good"]
