"""Behavioral contract for side-band streaming-retry observation."""

import pytest

from code_puppy.agents._runtime import streaming_retry


@pytest.mark.asyncio
async def test_observer_failure_cannot_change_retry_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def no_sleep(_: float) -> None:
        return None

    def broken_observer(_: BaseException) -> None:
        raise RuntimeError("observer failed")

    monkeypatch.setattr(
        "code_puppy.agents._runtime.asyncio.sleep",
        no_sleep,
    )
    monkeypatch.setattr(
        "code_puppy.agents._runtime.should_retry_streaming",
        lambda exc: True,
    )

    @streaming_retry(
        max_attempts=2,
        delays=(0,),
        observation_fn=broken_observer,
    )
    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("provider failed")
        return "ok"

    assert await operation() == "ok"
    assert attempts == 2


@pytest.mark.asyncio
async def test_observer_sees_non_retryable_exception_before_reraise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exc = ValueError("not retryable")
    observed: list[BaseException] = []

    monkeypatch.setattr(
        "code_puppy.agents._runtime.should_retry_streaming",
        lambda caught: False,
    )

    @streaming_retry(observation_fn=observed.append)
    async def operation() -> None:
        raise exc

    with pytest.raises(ValueError) as caught:
        await operation()

    assert caught.value is exc
    assert observed == [exc]
