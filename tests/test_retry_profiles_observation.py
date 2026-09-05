"""Contract for retry-policy observation forwarding."""

from typing import Any

from code_puppy.agents import retry_profiles


def test_make_streaming_retry_forwards_observation_fn(
    monkeypatch: Any,
) -> None:
    observer = object()
    captured: dict[str, Any] = {}
    sentinel = object()

    def fake_streaming_retry(**kwargs: Any) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(
        "code_puppy.agents._runtime.streaming_retry",
        fake_streaming_retry,
    )

    result = retry_profiles.make_streaming_retry(
        "main",
        observation_fn=observer,
    )

    assert result is sentinel
    assert captured["observation_fn"] is observer
