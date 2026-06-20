"""Centralized lazy loaders for optional model-provider dependencies."""

from __future__ import annotations

import importlib
from typing import Any

_PROVIDER_MAP = {
    "anthropic": {
        "members": {
            "AsyncAnthropic": "anthropic",
            "AnthropicModel": "pydantic_ai.models.anthropic",
            "AnthropicModelSettings": "pydantic_ai.models.anthropic",
        },
        "error": (
            "Anthropic models require the optional anthropic extra. "
            "Install it with: pip install 'code-puppy[anthropic]'"
        ),
    },
    "openai": {
        "members": {
            "OpenAIChatModel": "pydantic_ai.models.openai",
            "OpenAIChatModelSettings": "pydantic_ai.models.openai",
            "OpenAIResponsesModel": "pydantic_ai.models.openai",
            "OpenAIResponsesModelSettings": "pydantic_ai.models.openai",
            "OpenAIModelProfile": "pydantic_ai.profiles.openai",
            "CerebrasProvider": "pydantic_ai.providers.cerebras",
            "OpenRouterProvider": "pydantic_ai.providers.openrouter",
        },
        "error": (
            "OpenAI-compatible models require the optional openai extra. "
            "Install it with: pip install 'code-puppy[openai]'"
        ),
    },
    "azure": {
        "members": {
            "AsyncAzureOpenAI": "openai",
        },
        "error": (
            "Azure OpenAI models require the optional azure/openai extras. "
            "Install with: pip install 'code-puppy[azure,openai]'"
        ),
    },
    "cerebras": {
        "members": {
            "CerebrasProvider": "pydantic_ai.providers.cerebras",
        },
        "error": (
            "Cerebras models require the optional openai extra. "
            "Install it with: pip install 'code-puppy[openai]'"
        ),
    },
    "openrouter": {
        "members": {
            "OpenRouterProvider": "pydantic_ai.providers.openrouter",
        },
        "error": (
            "OpenRouter models require the optional openai extra. "
            "Install it with: pip install 'code-puppy[openai]'"
        ),
    },
}


def get_optional_provider_class(provider_name: str, class_name: str) -> Any:
    """Resolve an optional provider class or raise a friendly runtime error."""
    spec = _PROVIDER_MAP.get(provider_name)
    if spec is None:
        raise AttributeError(f"Unknown optional provider: {provider_name}")

    module_name = spec["members"].get(class_name)
    if module_name is None:
        raise AttributeError(
            f"Unknown optional class {class_name!r} for provider {provider_name!r}"
        )

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(spec["error"]) from exc
    return getattr(module, class_name)


def load_async_anthropic():
    return get_optional_provider_class("anthropic", "AsyncAnthropic")


def load_anthropic_model_classes():
    return (
        get_optional_provider_class("anthropic", "AnthropicModel"),
        get_optional_provider_class("anthropic", "AnthropicModelSettings"),
    )


def load_openai_model_classes():
    return (
        get_optional_provider_class("openai", "OpenAIChatModel"),
        get_optional_provider_class("openai", "OpenAIChatModelSettings"),
        get_optional_provider_class("openai", "OpenAIResponsesModel"),
        get_optional_provider_class("openai", "OpenAIResponsesModelSettings"),
    )


def load_async_azure_openai():
    return get_optional_provider_class("azure", "AsyncAzureOpenAI")


def load_openai_model_profile():
    return get_optional_provider_class("openai", "OpenAIModelProfile")


def load_cerebras_provider():
    return get_optional_provider_class("cerebras", "CerebrasProvider")


def load_openrouter_provider():
    return get_optional_provider_class("openrouter", "OpenRouterProvider")
