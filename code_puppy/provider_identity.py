"""Provider identity helpers for pydantic-ai compatibility boundaries.

pydantic-ai uses ``provider.name`` as the compatibility boundary for replaying
provider-specific thinking / provider_details. Code Puppy can route multiple
semantically different vendors through the same underlying provider classes,
so we need stable, distinct runtime identities.
"""

from __future__ import annotations

from typing import Any


def _load_anthropic_provider_class():
    try:
        from pydantic_ai.providers.anthropic import AnthropicProvider
    except ImportError as exc:  # pragma: no cover - optional extra absent
        raise RuntimeError(
            "Anthropic models require the optional anthropic extra. "
            "Install it with: pip install 'code-puppy[anthropic]'"
        ) from exc
    return AnthropicProvider


def _load_openai_provider_class():
    try:
        from pydantic_ai.providers.openai import OpenAIProvider
    except ImportError as exc:  # pragma: no cover - optional extra absent
        raise RuntimeError(
            "OpenAI-compatible models require the optional openai extra. "
            "Install it with: pip install 'code-puppy[openai]'"
        ) from exc
    return OpenAIProvider


_TYPE_PROVIDER_OVERRIDES = {
    "anthropic": "anthropic",
    "openai": "openai",
    "openrouter": "openrouter",
    "claude_code": "claude_code",
    "chatgpt_oauth": "chatgpt",
    "gemini": "google",
    "gemini_oauth": "google",
    "aws_bedrock": "aws_bedrock",
    "azure_openai": "azure_openai",
    "azure_foundry_openai": "azure_foundry_openai",
}

_KEY_PREFIX_OVERRIDES = (
    ("claude-code-", "claude_code"),
    ("chatgpt-", "chatgpt"),
    ("azure-openai-", "azure_openai"),
    ("openrouter-", "openrouter"),
)


def resolve_provider_identity(model_key: str, model_config: dict[str, Any]) -> str:
    """Resolve the canonical provider identity for a model config.

    Precedence:
    1. explicit ``model_config['provider']``
    2. type-specific overrides for known native/plugin model types
    3. known key-prefix overrides
    4. fallback to first token of model key
    5. conservative fallback for custom families
    """
    explicit_provider = model_config.get("provider")
    if isinstance(explicit_provider, str) and explicit_provider.strip():
        return explicit_provider.strip()

    model_type = model_config.get("type")
    if model_type in _TYPE_PROVIDER_OVERRIDES:
        return _TYPE_PROVIDER_OVERRIDES[model_type]

    for prefix, provider_name in _KEY_PREFIX_OVERRIDES:
        if model_key.startswith(prefix):
            return provider_name

    first_token = model_key.split("-", 1)[0].strip()
    if first_token and first_token != "custom":
        return first_token

    if model_type == "custom_anthropic":
        return "custom_anthropic"
    if model_type == "custom_openai":
        return "custom_openai"

    return model_type or "unknown"


def make_anthropic_provider(provider_name: str, **kwargs: Any) -> Any:
    """Create an Anthropic-family provider with a stable runtime name."""
    AnthropicProvider = _load_anthropic_provider_class()
    if provider_name == "anthropic":
        return AnthropicProvider(**kwargs)

    class AliasedAnthropicProvider(AnthropicProvider):
        """Anthropic provider with an overridable runtime identity."""

        def __init__(self, *args: Any, provider_name: str = "anthropic", **kwargs: Any):
            self._provider_name = provider_name
            super().__init__(*args, **kwargs)

        @property
        def name(self) -> str:
            return self._provider_name

    return AliasedAnthropicProvider(provider_name=provider_name, **kwargs)


def make_openai_provider(provider_name: str, **kwargs: Any) -> Any:
    """Create an OpenAI-family provider with a stable runtime name."""
    OpenAIProvider = _load_openai_provider_class()
    if provider_name == "openai":
        return OpenAIProvider(**kwargs)

    class AliasedOpenAIProvider(OpenAIProvider):
        """OpenAI provider with an overridable runtime identity."""

        def __init__(self, *args: Any, provider_name: str = "openai", **kwargs: Any):
            self._provider_name = provider_name
            super().__init__(*args, **kwargs)

        @property
        def name(self) -> str:
            return self._provider_name

    return AliasedOpenAIProvider(provider_name=provider_name, **kwargs)
