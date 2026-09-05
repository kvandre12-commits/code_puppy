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


def test_quota_observation_preserves_provider_vocabulary() -> None:
    from code_puppy.intelligence_registry import QuotaObservation

    provider_name = (
        "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    )

    observation = QuotaObservation(
        provider_name=provider_name,
        limit=20,
        remaining=0,
        window="day",
        source="provider_error",
    )

    assert observation.provider_name == provider_name
    assert observation.limit == 20
    assert observation.remaining == 0
    assert observation.window == "day"
    assert observation.source == "provider_error"


def test_quota_observations_are_not_shared_between_resources() -> None:
    from code_puppy.intelligence_registry import QuotaObservation

    first = make_resource("first/resource")
    second = make_resource("second/resource")

    first.economics.quota_observations.append(
        QuotaObservation(
            provider_name="premium_requests",
            remaining=10,
            source="provider_usage",
        )
    )

    assert len(first.economics.quota_observations) == 1
    assert second.economics.quota_observations == []


def test_scrubber_preserves_structured_google_quota_failure() -> None:
    from code_puppy.intelligence_registry import scrub_quota_observations

    exc = RuntimeError(
        """Gemini API error 429: {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-3.6-flash"
            },
            "quotaValue": "20"
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.RetryInfo",
        "retryDelay": "17s"
      }
    ]
  }
}"""
    )

    observations = scrub_quota_observations(exc)

    assert len(observations) == 1

    observation = observations[0]
    assert (
        observation.provider_name
        == "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    )
    assert (
        observation.provider_metric
        == "generativelanguage.googleapis.com/generate_content_free_tier_requests"
    )
    assert observation.provider_dimensions == {
        "location": "global",
        "model": "gemini-3.6-flash",
    }
    assert observation.limit == 20.0
    assert observation.source == "provider_error"


def test_scrubber_does_not_infer_quota_from_generic_429() -> None:
    from code_puppy.intelligence_registry import scrub_quota_observations

    exc = RuntimeError("429 Too Many Requests")

    observations = scrub_quota_observations(exc)

    assert observations == ()



def test_resource_from_model_config_preserves_configured_identity() -> None:
    from code_puppy.intelligence_registry import resource_from_model_config

    resource = resource_from_model_config(
        "google-gemini-3.6-flash",
        {
            "type": "gemini",
            "provider": "google",
            "name": "gemini-3.6-flash",
        },
    )

    assert resource.id == "google-gemini-3.6-flash"
    assert resource.provider == "google"
    assert resource.model == "gemini-3.6-flash"


def test_resource_from_model_config_keeps_same_model_on_distinct_resources() -> None:
    from code_puppy.intelligence_registry import resource_from_model_config

    personal = resource_from_model_config(
        "google-personal-gemini-3.6-flash",
        {
            "type": "gemini",
            "provider": "google",
            "name": "gemini-3.6-flash",
        },
    )
    student = resource_from_model_config(
        "google-student-gemini-3.6-flash",
        {
            "type": "gemini",
            "provider": "google",
            "name": "gemini-3.6-flash",
        },
    )

    assert personal.id != student.id
    assert personal.provider == student.provider == "google"
    assert personal.model == student.model == "gemini-3.6-flash"
