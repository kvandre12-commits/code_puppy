"""OpenRouter model catalog plugin.

This plugin wires Code Puppy to OpenRouter using a single environment variable:

    OPENROUTER_API_KEY

No secret is stored in code. Model entries reference the key as
``$OPENROUTER_API_KEY`` so the normal Code Puppy credential resolver can use
puppy.cfg or environment variables.

Optional environment variables:
- CODE_PUPPY_OPENROUTER_MODELS="alias=model/id,alias2=provider/model"
- CODE_PUPPY_OPENROUTER_INCLUDE_PRESETS=0  # disable bundled convenience aliases
- CODE_PUPPY_OPENROUTER_ROTATE_EVERY=1     # round-robin rotation interval
"""

from __future__ import annotations

import os
from typing import Any

from code_puppy.callbacks import register_callback
from code_puppy.messaging import emit_info, emit_success, emit_warning
from code_puppy.provider_credentials import is_credential_set, mask_secret

API_KEY_ENV = "OPENROUTER_API_KEY"
CUSTOM_MODELS_ENV = "CODE_PUPPY_OPENROUTER_MODELS"
INCLUDE_PRESETS_ENV = "CODE_PUPPY_OPENROUTER_INCLUDE_PRESETS"
ROTATE_EVERY_ENV = "CODE_PUPPY_OPENROUTER_ROTATE_EVERY"

# Conservative convenience aliases. OpenRouter model slugs can change over time,
# so users can override/replace these with CODE_PUPPY_OPENROUTER_MODELS.
PRESET_MODELS: dict[str, tuple[str, int, str]] = {
    "openrouter-auto": (
        "openrouter/auto",
        128_000,
        "OpenRouter automatic router using one OPENROUTER_API_KEY.",
    ),
    "openrouter-sonnet": (
        "anthropic/claude-sonnet-4.5",
        200_000,
        "Claude Sonnet via OpenRouter; strong coding/reasoning when available.",
    ),
    "openrouter-gpt-mini": (
        "openai/gpt-5-mini",
        128_000,
        "OpenAI GPT mini-class model via OpenRouter when available.",
    ),
    "openrouter-qwen-coder": (
        "qwen/qwen3-coder",
        128_000,
        "Qwen coder model via OpenRouter when available.",
    ),
}


def _slugify_alias(alias: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in alias.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def _model_entry(
    model_id: str, context_length: int, description: str
) -> dict[str, Any]:
    return {
        "type": "openrouter",
        "provider": "openrouter",
        "name": model_id,
        "api_key": f"${API_KEY_ENV}",
        "context_length": context_length,
        "description": description,
    }


def _parse_custom_models() -> dict[str, tuple[str, int, str]]:
    """Parse CODE_PUPPY_OPENROUTER_MODELS into alias -> model config tuples.

    Format:
        alias=model/id,alias2=provider/model

    Optional context length suffix:
        alias=model/id:200000
    """
    raw = os.environ.get(CUSTOM_MODELS_ENV, "").strip()
    if not raw:
        return {}

    parsed: dict[str, tuple[str, int, str]] = {}
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item or "=" not in item:
            continue
        alias_raw, model_raw = item.split("=", 1)
        alias = _slugify_alias(alias_raw)
        if not alias:
            continue
        if not alias.startswith("openrouter-"):
            alias = f"openrouter-{alias}"

        model_id = model_raw.strip()
        context_length = 128_000
        if ":" in model_id:
            candidate_model, candidate_ctx = model_id.rsplit(":", 1)
            try:
                context_length = int(candidate_ctx.replace("_", ""))
                model_id = candidate_model.strip()
            except ValueError:
                # Keep the full model id if suffix is not numeric.
                pass
        if not model_id:
            continue

        parsed[alias] = (
            model_id,
            context_length,
            f"User-configured OpenRouter model {model_id}.",
        )
    return parsed


def _load_openrouter_models_config() -> dict[str, Any]:
    include_presets = os.environ.get(INCLUDE_PRESETS_ENV, "1").strip() not in {
        "0",
        "false",
        "False",
        "no",
        "NO",
    }

    specs: dict[str, tuple[str, int, str]] = {}
    if include_presets:
        specs.update(PRESET_MODELS)
    specs.update(_parse_custom_models())

    models: dict[str, Any] = {
        alias: _model_entry(model_id, context_length, description)
        for alias, (model_id, context_length, description) in specs.items()
    }

    cycle_members = [name for name in models if name != "openrouter-auto"]
    if not cycle_members:
        cycle_members = ["openrouter-auto"] if "openrouter-auto" in models else []

    if len(cycle_members) >= 2:
        try:
            rotate_every = int(os.environ.get(ROTATE_EVERY_ENV, "1"))
        except ValueError:
            rotate_every = 1
        models["openrouter-cycle"] = {
            "type": "round_robin",
            "provider": "openrouter",
            "models": cycle_members,
            "rotate_every": max(1, rotate_every),
            "context_length": max(
                int(models[name].get("context_length", 128_000))
                for name in cycle_members
            ),
            "description": "Round-robin cycle across configured OpenRouter model aliases using one OPENROUTER_API_KEY.",
        }

    return models


def _load_openrouter_descriptions() -> dict[str, str]:
    return {
        name: cfg.get("description", "")
        for name, cfg in _load_openrouter_models_config().items()
        if isinstance(cfg, dict) and cfg.get("description")
    }


def _openrouter_status() -> None:
    emit_info("")
    emit_info("OpenRouter Status")
    emit_info("=" * 40)

    key_value = os.environ.get(API_KEY_ENV)
    if is_credential_set(API_KEY_ENV):
        emit_success(f"{API_KEY_ENV}: configured {mask_secret(key_value)}")
    else:
        emit_warning(f"{API_KEY_ENV}: not set")
        emit_info(f"Set it with: export {API_KEY_ENV}=<your-openrouter-key>")

    models = _load_openrouter_models_config()
    emit_info(f"Configured OpenRouter aliases: {len(models)}")
    for name, cfg in sorted(models.items()):
        if cfg.get("type") == "round_robin":
            emit_info(f"  - {name}: cycle {cfg.get('models', [])}")
        else:
            emit_info(f"  - {name}: {cfg.get('name')}")
    emit_info("")


def _custom_help() -> list[tuple[str, str]]:
    return [
        ("openrouter-status", "Show OpenRouter key status and configured model aliases")
    ]


def _handle_custom_command(command: str, name: str) -> bool | str | None:
    if name != "openrouter-status":
        return None
    _openrouter_status()
    return True


register_callback("load_models_config", _load_openrouter_models_config)
register_callback("load_model_descriptions", _load_openrouter_descriptions)
register_callback("custom_command", _handle_custom_command)
register_callback("custom_command_help", _custom_help)
