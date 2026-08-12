"""Shared OpenAI-family capability helpers.

Keep transport/capability inference in one place instead of repeating fragile
name sniffing across model factory, discovery importers, and request shims.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal

OpenAITransport = Literal["chat", "responses"]

_DEFAULT_REASONING_EFFORT_CHOICES = ("minimal", "low", "medium", "high")
_SOL_REASONING_EFFORT_CHOICES = ("none", "low", "medium", "high", "xhigh", "max")
_REASONING_EFFORT_RANK = {
    "none": 0,
    "minimal": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "xhigh": 4,
    "max": 5,
}


def _normalized_model_identifiers(
    model_name: str, model_config: dict[str, Any] | None = None
) -> tuple[str, ...]:
    """Return normalized alias/model-id candidates for family checks."""
    candidates: list[str] = []
    seen: set[str] = set()

    for value in (
        model_name,
        model_config.get("name") if isinstance(model_config, dict) else None,
        model_config.get("model") if isinstance(model_config, dict) else None,
    ):
        if not isinstance(value, str):
            continue
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)

    return tuple(candidates)


def _explicit_openai_transport(
    model_config: dict[str, Any] | None = None,
) -> OpenAITransport | None:
    if not isinstance(model_config, dict):
        return None

    for key in ("openai_transport", "api_format", "transport"):
        value = model_config.get(key)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"chat", "responses"}:
                return normalized
    return None


def _explicit_openai_family(model_config: dict[str, Any] | None = None) -> str | None:
    if not isinstance(model_config, dict):
        return None
    value = model_config.get("openai_family")
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _configured_reasoning_effort_choices(
    model_config: dict[str, Any] | None = None,
) -> tuple[str, ...] | None:
    if not isinstance(model_config, dict):
        return None
    values = model_config.get("reasoning_effort_choices")
    if not isinstance(values, list):
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return tuple(normalized) if normalized else None


def is_openai_sol_family(
    model_name: str, model_config: dict[str, Any] | None = None
) -> bool:
    """Return whether a model refers to OpenAI's Sol reasoning tier."""
    if _explicit_openai_family(model_config) == "sol":
        return True

    identifiers = _normalized_model_identifiers(model_name, model_config)
    return any(
        identifier.endswith("-sol") or identifier.startswith("sol")
        for identifier in identifiers
    )


def supports_openai_reasoning_payload(
    model_name: str, model_config: dict[str, Any] | None = None
) -> bool:
    """Return whether the model should get OpenAI reasoning payload fields."""
    if is_openai_sol_family(model_name, model_config):
        return True

    identifiers = _normalized_model_identifiers(model_name, model_config)
    reasoning_prefixes = ("gpt-5", "o1", "o3", "o4")
    return any(
        identifier.startswith(reasoning_prefixes) or "codex" in identifier
        for identifier in identifiers
    )


def infer_openai_transport(
    model_name: str, model_config: dict[str, Any] | None = None
) -> OpenAITransport:
    """Infer whether an OpenAI-family model should use chat or responses."""
    explicit_transport = _explicit_openai_transport(model_config)
    if explicit_transport is not None:
        return explicit_transport

    model_type = ""
    if isinstance(model_config, dict):
        raw_type = model_config.get("type")
        if isinstance(raw_type, str):
            model_type = raw_type.strip().lower()

    identifiers = _normalized_model_identifiers(model_name, model_config)
    if model_type == "chatgpt_oauth":
        return "responses"
    if any("codex" in identifier for identifier in identifiers):
        return "responses"
    if is_openai_sol_family(model_name, model_config):
        return "responses"
    if model_type == "azure_foundry_openai" and any(
        identifier.startswith("gpt-5") for identifier in identifiers
    ):
        return "responses"
    return "chat"


def supports_openai_xhigh_reasoning(
    model_name: str, model_config: dict[str, Any] | None = None
) -> bool:
    """Return whether the model should expose xhigh reasoning effort."""
    if isinstance(model_config, dict):
        explicit = model_config.get("supports_xhigh_reasoning")
        if isinstance(explicit, bool):
            return explicit

    identifiers = _normalized_model_identifiers(model_name, model_config)
    if is_openai_sol_family(model_name, model_config):
        return True
    return any(
        "codex" in identifier or identifier.startswith(("gpt-5.4", "gpt-5.5"))
        for identifier in identifiers
    )


def get_openai_reasoning_effort_choices(
    model_name: str, model_config: dict[str, Any] | None = None
) -> tuple[str, ...]:
    """Return the allowed reasoning effort choices for a model."""
    configured_choices = _configured_reasoning_effort_choices(model_config)
    if configured_choices is not None:
        return configured_choices

    if is_openai_sol_family(model_name, model_config):
        return _SOL_REASONING_EFFORT_CHOICES

    choices = list(_DEFAULT_REASONING_EFFORT_CHOICES)
    if supports_openai_xhigh_reasoning(model_name, model_config):
        choices.append("xhigh")
    return tuple(choices)


def normalize_openai_reasoning_effort(
    model_name: str,
    value: str | None,
    model_config: dict[str, Any] | None = None,
    *,
    default: str = "medium",
) -> str:
    """Clamp/translate a configured reasoning effort to what a model supports."""
    normalized = (value or default).strip().lower() or default
    choices = get_openai_reasoning_effort_choices(model_name, model_config)

    if normalized == "minimal" and "minimal" not in choices and "none" in choices:
        normalized = "none"
    elif normalized == "none" and "none" not in choices and "minimal" in choices:
        normalized = "minimal"

    if normalized in choices:
        return normalized

    target_rank = _REASONING_EFFORT_RANK.get(
        normalized, _REASONING_EFFORT_RANK.get(default, 2)
    )

    best_choice = choices[0]
    best_rank = _REASONING_EFFORT_RANK.get(best_choice, 0)
    for choice in choices:
        rank = _REASONING_EFFORT_RANK.get(choice, 0)
        if rank <= target_rank and rank >= best_rank:
            best_choice = choice
            best_rank = rank

    return best_choice


def merge_openai_metadata(
    model_name: str,
    model_config: dict[str, Any] | None = None,
    *,
    supported_settings: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Merge shared OpenAI capability metadata into a model config copy."""
    merged: dict[str, Any] = dict(model_config or {})

    if supported_settings is None:
        existing_settings = merged.get("supported_settings")
        iterable = existing_settings if isinstance(existing_settings, list) else []
    else:
        iterable = supported_settings

    normalized_settings: list[str] = []
    seen_settings: set[str] = set()
    for setting in iterable:
        if not isinstance(setting, str) or setting in seen_settings:
            continue
        seen_settings.add(setting)
        normalized_settings.append(setting)

    if is_openai_sol_family(model_name, merged):
        merged.setdefault("openai_family", "sol")
        merged.setdefault(
            "reasoning_effort_choices", list(_SOL_REASONING_EFFORT_CHOICES)
        )
        for setting in ("reasoning_effort", "summary", "verbosity"):
            if setting not in seen_settings:
                seen_settings.add(setting)
                normalized_settings.append(setting)
        merged.setdefault("openai_transport", "responses")

    if normalized_settings:
        merged["supported_settings"] = normalized_settings

    if supports_openai_xhigh_reasoning(model_name, merged):
        merged["supports_xhigh_reasoning"] = True

    return merged
