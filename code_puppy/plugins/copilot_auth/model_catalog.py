"""GitHub Copilot model-catalog helpers.

The Copilot ``/models`` endpoint can advertise model IDs that the chat API later
rejects with ``model_not_supported`` for the current account, endpoint, or
entitlement.  This module keeps registration honest by preserving catalogue
models, but pruning only models that the chat endpoint clearly rejects.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

import requests

from .config import COPILOT_AUTH_CONFIG, DEFAULT_COPILOT_MODELS

logger = logging.getLogger(__name__)

_MODEL_NOT_SUPPORTED_CODES = {
    "model_not_supported",
    "model_not_found",
    "unknown_model",
}


def fetch_supported_copilot_models(
    session_token: str,
    host: str,
    api_base: str,
) -> list[str]:
    """Fetch and prune Copilot models to those accepted by chat completions.

    We still trust the catalogue for discovery, but GitHub's chat endpoint is
    the source of truth for whether a model is usable *right now* for this
    token.  Only explicit model-not-supported responses are removed; rate
    limits, auth hiccups, and unrelated parameter errors keep the model so we
    do not accidentally hide valid options.
    """
    entries = _fetch_model_entries(session_token, api_base)
    model_ids = _extract_chat_candidate_ids(entries)
    if not model_ids:
        logger.info("Using default Copilot model list for %s", host)
        model_ids = list(DEFAULT_COPILOT_MODELS)

    supported = filter_chat_supported_models(session_token, api_base, model_ids)
    if not supported:
        logger.warning(
            "Copilot model validation removed every candidate for %s; keeping raw list",
            host,
        )
        return model_ids
    return supported


def filter_chat_supported_models(
    session_token: str,
    api_base: str,
    model_ids: Iterable[str],
) -> list[str]:
    """Drop models that clearly fail chat completions with model_not_supported."""
    kept: list[str] = []
    rejected: list[str] = []

    for model_id in _dedupe(model_ids):
        if _chat_endpoint_accepts_model(session_token, api_base, model_id):
            kept.append(model_id)
        else:
            rejected.append(model_id)

    if rejected:
        logger.info(
            "Filtered %d Copilot model(s) rejected by chat endpoint: %s",
            len(rejected),
            ", ".join(rejected),
        )
    return kept


def _fetch_model_entries(session_token: str, api_base: str) -> list[Any]:
    url = f"{api_base.rstrip('/')}/models"
    headers = _copilot_headers(session_token)
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.debug(
                "Copilot model catalogue fetch failed: %s %s",
                resp.status_code,
                resp.text[:200],
            )
            return []
        data = resp.json()
    except Exception as exc:
        logger.debug("Could not fetch Copilot model list: %s", exc)
        return []

    model_list = data.get("data") or data.get("models") or []
    if not isinstance(model_list, list):
        return []
    logger.info("Fetched %d models from Copilot API", len(model_list))
    return model_list


def _extract_chat_candidate_ids(entries: Iterable[Any]) -> list[str]:
    ids: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            model_id = entry
            metadata: Mapping[str, Any] = {}
        elif isinstance(entry, Mapping):
            model_id = str(entry.get("id") or entry.get("name") or "").strip()
            metadata = entry
        else:
            continue

        if not model_id:
            continue
        if _metadata_rules_out_chat(model_id, metadata):
            continue
        ids.append(model_id)
    return _dedupe(ids)


def _metadata_rules_out_chat(model_id: str, metadata: Mapping[str, Any]) -> bool:
    """Return True only when catalogue metadata clearly says "not chat"."""
    lower_id = model_id.lower()
    if "embedding" in lower_id or lower_id.startswith("text-embedding"):
        return True

    if metadata.get("disabled") is True or metadata.get("enabled") is False:
        return True
    if metadata.get("model_picker_enabled") is False:
        return True

    capabilities = metadata.get("capabilities")
    if isinstance(capabilities, Mapping):
        model_type = str(capabilities.get("type") or "").lower()
        if model_type and model_type not in {"chat", "completion", "chat_completion"}:
            return True

        endpoint_values = _flatten_strings(
            capabilities.get("endpoints"),
            capabilities.get("supported_endpoints"),
            capabilities.get("supports"),
        )
        if endpoint_values and not _contains_chat_endpoint(endpoint_values):
            return True

    endpoint_values = _flatten_strings(
        metadata.get("endpoints"),
        metadata.get("supported_endpoints"),
    )
    if endpoint_values and not _contains_chat_endpoint(endpoint_values):
        return True

    return False


def _chat_endpoint_accepts_model(
    session_token: str,
    api_base: str,
    model_id: str,
) -> bool:
    """Probe chat completions and reject only explicit unsupported-model errors."""
    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with ok."}],
        "max_tokens": 1,
        "stream": False,
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=_copilot_headers(session_token),
            timeout=20,
        )
    except Exception as exc:
        logger.debug("Could not validate Copilot model %s: %s", model_id, exc)
        return True

    if resp.status_code < 400:
        return True
    return not _is_model_not_supported_response(resp)


def _is_model_not_supported_response(resp: requests.Response) -> bool:
    try:
        data = resp.json()
    except Exception:
        data = {}

    error = data.get("error") if isinstance(data, Mapping) else None
    if isinstance(error, Mapping):
        code = str(error.get("code") or error.get("type") or "").lower()
        message = str(error.get("message") or "").lower()
    else:
        code = str(data.get("code") or "").lower() if isinstance(data, Mapping) else ""
        message = str(data.get("message") or resp.text or "").lower()

    return code in _MODEL_NOT_SUPPORTED_CODES or "model_not_supported" in message


def _copilot_headers(session_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {session_token}",
        "Accept": "application/json",
        "Editor-Version": COPILOT_AUTH_CONFIG["editor_version"],
        "Editor-Plugin-Version": COPILOT_AUTH_CONFIG["editor_plugin_version"],
        "Copilot-Integration-Id": COPILOT_AUTH_CONFIG["copilot_integration_id"],
        "Openai-Intent": COPILOT_AUTH_CONFIG["openai_intent"],
    }


def _contains_chat_endpoint(values: Iterable[str]) -> bool:
    for value in values:
        normal = value.lower().replace("_", "-")
        if "chat" in normal or "chat/completions" in normal:
            return True
    return False


def _flatten_strings(*values: Any) -> list[str]:
    flattened: list[str] = []
    for value in values:
        if isinstance(value, str):
            flattened.append(value)
        elif isinstance(value, Mapping):
            flattened.extend(str(k) for k, v in value.items() if bool(v))
        elif isinstance(value, Iterable):
            flattened.extend(str(item) for item in value)
    return flattened


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
