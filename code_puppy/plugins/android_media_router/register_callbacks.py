"""Register Android media router tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_media_router_doctor as android_media_router_doctor_impl,
    android_media_router_examples as android_media_router_examples_impl,
    handle_transcript as sharpedge_media_handle_transcript_impl,
    set_favorite as sharpedge_media_set_favorite_impl,
    sharpedge_play as sharpedge_play_impl,
)

_DOCTOR = "android_media_router_doctor"
_PLAY = "sharpedge_play"
_HANDLE = "sharpedge_media_handle_transcript"
_SET_FAVORITE = "sharpedge_media_set_favorite"
_EXAMPLES = "android_media_router_examples"


def register_android_media_router_doctor(agent: Any) -> None:
    @agent.tool
    async def android_media_router_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_media_router_doctor_impl()


def register_sharpedge_play(agent: Any) -> None:
    @agent.tool
    async def sharpedge_play(
        context: RunContext,
        query: str = "",
        provider: str = "auto",
        favorite: bool = False,
        dry_run: bool = True,
        music_volume: int | None = 12,
        press_play: bool = True,
    ) -> dict[str, Any]:
        del context
        return sharpedge_play_impl(
            query=query,
            provider=provider,
            favorite=favorite,
            dry_run=dry_run,
            music_volume=music_volume,
            press_play=press_play,
        )


def register_sharpedge_media_handle_transcript(agent: Any) -> None:
    @agent.tool
    async def sharpedge_media_handle_transcript(
        context: RunContext,
        transcript: str,
        dry_run: bool = True,
        music_volume: int | None = 12,
    ) -> dict[str, Any]:
        del context
        return sharpedge_media_handle_transcript_impl(
            transcript=transcript,
            dry_run=dry_run,
            music_volume=music_volume,
        )


def register_sharpedge_media_set_favorite(agent: Any) -> None:
    @agent.tool
    async def sharpedge_media_set_favorite(
        context: RunContext,
        target: str,
        provider: str = "youtube",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return sharpedge_media_set_favorite_impl(
            target=target,
            provider=provider,
            dry_run=dry_run,
        )


def register_android_media_router_examples(agent: Any) -> None:
    @agent.tool
    async def android_media_router_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_media_router_examples_impl()


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_media_router_doctor},
        {"name": _PLAY, "register_func": register_sharpedge_play},
        {"name": _HANDLE, "register_func": register_sharpedge_media_handle_transcript},
        {"name": _SET_FAVORITE, "register_func": register_sharpedge_media_set_favorite},
        {"name": _EXAMPLES, "register_func": register_android_media_router_examples},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _PLAY, _HANDLE, _SET_FAVORITE, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
