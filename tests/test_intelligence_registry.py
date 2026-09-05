"""Tests for the provider-agnostic intelligence resource registry."""

from __future__ import annotations

import pytest

from code_puppy.intelligence_registry import (
    AuthType,
    Capability,
    IntelligenceRegistry,
    IntelligenceResource,
    ProbeResult,
    ResourceStatus,
)


def make_resource(
    resource_id: str = "google-personal/gemini-3.6-flash",
) -> IntelligenceResource:
    return IntelligenceResource(
        id=resource_id,
        provider="google",
        model="gemini-3.6-flash",
        auth_type=AuthType.API_KEY,
        entitlement="personal-free",
        capabilities={
            Capability.REASONING,
            Capability.CODING,
            Capability.TOOL_USE,
        },
    )


def test_register_and_get_resource() -> None:
    registry = IntelligenceRegistry()
    resource = make_resource()

    registry.register(resource)

    assert registry.get(resource.id) is resource
    assert registry.all() == (resource,)


def test_duplicate_resource_id_is_rejected() -> None:
    registry = IntelligenceRegistry()
    resource = make_resource()

    registry.register(resource)

    with pytest.raises(ValueError, match="resource already registered"):
        registry.register(make_resource())


def test_available_requires_ready_status() -> None:
    registry = IntelligenceRegistry()
    resource = make_resource()
    registry.register(resource)

    assert registry.available() == ()

    registry.record_probe(resource.id, ProbeResult(succeeded=True))

    assert registry.available() == (resource,)
    assert resource.status is ResourceStatus.READY


def test_available_filters_by_capability() -> None:
    registry = IntelligenceRegistry()
    resource = make_resource()
    registry.register(resource)
    registry.record_probe(resource.id, ProbeResult(succeeded=True))

    assert registry.available({Capability.CODING}) == (resource,)
    assert registry.available({Capability.VISION}) == ()


def test_failed_probe_marks_resource_degraded() -> None:
    registry = IntelligenceRegistry()
    resource = make_resource()
    registry.register(resource)

    result = ProbeResult(
        succeeded=False,
        error_type="quota",
        detail="bounded test failure",
    )
    registry.record_probe(resource.id, result)

    assert resource.last_probe is result
    assert resource.status is ResourceStatus.DEGRADED
    assert registry.available() == ()


def test_probe_for_unknown_resource_is_rejected() -> None:
    registry = IntelligenceRegistry()

    with pytest.raises(KeyError, match="unknown resource"):
        registry.record_probe(
            "missing/resource",
            ProbeResult(succeeded=True),
        )
