from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

STATE_PATH = Path.home() / ".code_puppy" / "sharpedge_media.json"
LEGACY_FAVORITE_PATH = Path("outputs/sharpedge_favorite_youtube.txt")

SPOTIFY_PACKAGE = "com.spotify.music"
YOUTUBE_PACKAGE = "com.google.android.youtube"
YOUTUBE_MUSIC_PACKAGE = "com.google.android.apps.youtube.music"

FAVORITE_QUERY = "Jack Harlow Tyler Herro remix"
FIGHT_SONG_LABEL = "Eye of the Tiger - Survivor"
FIGHT_SONG_URI = "spotify:track:2HHtWyy5CgaQbC7XSoOb0e"

PROVIDERS = {"auto", "spotify", "youtube", "youtube_music", "browser"}
BEEP_STREAMS = ("notification", "system")


class SpeechListenError(RuntimeError):
    pass


class MediaRouteError(ValueError):
    pass


def _normalize(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _which(command: str) -> str | None:
    return shutil.which(command)


def _run(args: list[str], *, dry_run: bool, timeout: int = 30) -> dict[str, Any]:
    if dry_run:
        return {"success": True, "dry_run": True, "args": args}
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "success": False,
            "dry_run": False,
            "args": args,
            "error": f"command not found: {exc.filename or args[0]}",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "dry_run": False,
            "args": args,
            "error": f"command timed out after {timeout}s",
        }
    return {
        "success": completed.returncode == 0 and "Error:" not in completed.stderr,
        "dry_run": False,
        "args": args,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _legacy_favorite() -> str:
    try:
        if LEGACY_FAVORITE_PATH.exists():
            return LEGACY_FAVORITE_PATH.read_text().strip()
    except OSError:
        pass
    return ""


def _default_state() -> dict[str, str]:
    return {
        "favorite_provider": "youtube",
        "favorite_target": _legacy_favorite() or FAVORITE_QUERY,
    }


def read_state() -> dict[str, str]:
    state = _default_state()
    try:
        if STATE_PATH.exists():
            loaded = json.loads(STATE_PATH.read_text())
            if isinstance(loaded, dict):
                for key in state:
                    if isinstance(loaded.get(key), str):
                        state[key] = loaded[key]
    except (OSError, json.JSONDecodeError):
        pass
    if not state["favorite_target"].strip():
        state["favorite_target"] = FAVORITE_QUERY
    return state


def _write_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _validate_provider(provider: str) -> str:
    selected = _normalize(provider or "auto").replace(" ", "_")
    if selected not in PROVIDERS:
        raise MediaRouteError(f"provider must be one of {sorted(PROVIDERS)}")
    return selected


def _explicit_provider_from_text(text: str) -> str:
    normalized = _normalize(text)
    if re.search(r"\b(?:on|in)\s+youtube\s+music\b", normalized):
        return "youtube_music"
    if re.search(r"\b(?:on|in)\s+spotify\b", normalized):
        return "spotify"
    if re.search(r"\b(?:on|in)\s+youtube\b", normalized):
        return "youtube"
    if re.search(r"\b(?:on|in)\s+(?:browser|website)\b", normalized):
        return "browser"
    return "auto"


def _provider_for(target: str, requested: str) -> str:
    provider = _validate_provider(requested)
    if provider != "auto":
        return provider
    if target.startswith(("spotify:", "https://open.spotify.com/")):
        return "spotify"
    if target.startswith("https://music.youtube.com/"):
        return "youtube_music"
    if target.startswith(
        ("https://youtu.be/", "https://www.youtube.com/", "https://m.youtube.com/")
    ):
        return "youtube"
    return "youtube"


def _package_for(provider: str) -> str:
    return {
        "spotify": SPOTIFY_PACKAGE,
        "youtube": YOUTUBE_PACKAGE,
        "youtube_music": YOUTUBE_MUSIC_PACKAGE,
    }.get(provider, "")


def _url_for(target: str, provider: str) -> str:
    if target.startswith(("http://", "https://", "spotify:")):
        return target
    query = quote_plus(target)
    if provider == "spotify":
        return f"https://open.spotify.com/search/{query}"
    if provider == "youtube_music":
        return f"https://music.youtube.com/search?q={query}"
    if provider == "youtube":
        return f"https://www.youtube.com/results?search_query={query}"
    return f"https://www.google.com/search?q={query}"


def _intent_command(url: str, provider: str) -> list[str]:
    command = ["am", "start", "-a", "android.intent.action.VIEW"]
    package_name = _package_for(provider)
    # YouTube rejects forced-package web search URLs on this device.
    # Let Android verified links pick the app. Spotify URI routing is explicit.
    if package_name and provider in {"spotify", "youtube_music"}:
        command.extend(["-p", package_name])
    command.extend(["-d", url])
    return command


def set_favorite(
    target: str, provider: str = "youtube", dry_run: bool = True
) -> dict[str, Any]:
    target = target.strip()
    if not target:
        raise MediaRouteError("favorite target is required")
    selected_provider = _provider_for(target, provider)
    state = {"favorite_provider": selected_provider, "favorite_target": target}
    if not dry_run:
        _write_state(state)
        if selected_provider in {"youtube", "youtube_music"}:
            LEGACY_FAVORITE_PATH.parent.mkdir(parents=True, exist_ok=True)
            LEGACY_FAVORITE_PATH.write_text(target + "\n")
    return {"success": True, "dry_run": dry_run, "state_path": str(STATE_PATH), **state}


def _route(query: str, provider: str, favorite: bool) -> dict[str, Any]:
    state = read_state()
    target = state["favorite_target"] if favorite else query.strip()
    requested_provider = (
        state["favorite_provider"] if favorite and provider == "auto" else provider
    )
    if not target:
        raise MediaRouteError("query is required unless favorite=True")

    is_fight_song = bool(re.search(r"\b(fight|hype|workout)\s+song\b", target, re.I))
    if is_fight_song:
        target = FIGHT_SONG_URI
        requested_provider = "spotify"

    resolved_provider = _provider_for(target, requested_provider)
    url = _url_for(target, resolved_provider)
    label = FIGHT_SONG_LABEL if target == FIGHT_SONG_URI else target
    return {
        "provider": resolved_provider,
        "package_name": _package_for(resolved_provider),
        "target": target,
        "label": label,
        "url": url,
        "command": _intent_command(url, resolved_provider),
        "press_play_allowed": target != FIGHT_SONG_URI,
    }


def sharpedge_play(
    query: str = "",
    provider: str = "auto",
    favorite: bool = False,
    dry_run: bool = True,
    music_volume: int | None = 12,
    press_play: bool = False,
) -> dict[str, Any]:
    route = _route(query=query, provider=provider, favorite=favorite)
    actions: list[dict[str, Any]] = []
    if music_volume is not None:
        bounded_volume = max(0, min(15, int(music_volume)))
        actions.append(
            {
                "name": "set_music_volume",
                "result": _run(
                    ["termux-volume", "music", str(bounded_volume)], dry_run=dry_run
                ),
            }
        )
    open_result = _run(route["command"], dry_run=dry_run)
    actions.append({"name": "open_media", "result": open_result})

    if press_play and route["press_play_allowed"]:
        if not dry_run:
            time.sleep(1)
        actions.append(
            {
                "name": "press_media_play",
                "result": _run(
                    ["input", "keyevent", "KEYCODE_MEDIA_PLAY"], dry_run=dry_run
                ),
            }
        )
    elif press_play:
        actions.append(
            {
                "name": "press_media_play_skipped",
                "reason": "fight song uses a Spotify deeplink; generic media play can resume stale queue",
            }
        )

    route.pop("press_play_allowed", None)
    return {
        "success": open_result.get("success", False),
        "dry_run": dry_run,
        **route,
        "actions": actions,
    }


def _has_wake_word(text: str) -> bool:
    normalized = _normalize(text)
    return "sharpedge" in normalized.replace(" ", "") or "sharp edge" in normalized


def _favorite_assignment(text: str) -> str:
    match = re.search(
        r"(?:set\s+my\s+favorite\s+song\s+to|set\s+favorite\s+song\s+to|my\s+favorite\s+song\s+is|favorite\s+song\s+is)\s+(.+)",
        text,
        flags=re.I,
    )
    return match.group(1).strip(" .,!") if match else ""


def _play_query(text: str) -> str:
    cleaned = re.sub(r"\b(?:hey\s+)?sharp\s*edge\b", "", text, flags=re.I)
    cleaned = re.sub(r"\bsharpedge\b", "", cleaned, flags=re.I)
    cleaned = re.sub(
        r"\b(on|in)\s+(spotify|youtube music|youtube|browser|website)\b",
        "",
        cleaned,
        flags=re.I,
    )
    match = re.search(r"\b(?:play|open)\s+(.+)", cleaned, flags=re.I)
    return match.group(1).strip(" .,!") if match else ""


def handle_transcript(
    transcript: str, dry_run: bool = True, music_volume: int | None = 12
) -> dict[str, Any]:
    if not _has_wake_word(transcript):
        return {
            "success": False,
            "ignored": True,
            "message": "wake word 'SharpEdge' not heard",
        }

    provider = _explicit_provider_from_text(transcript)
    favorite_target = _favorite_assignment(transcript)
    if favorite_target:
        return set_favorite(favorite_target, provider=provider, dry_run=dry_run)

    normalized = _normalize(transcript)
    if "favorite song" in normalized:
        return sharpedge_play(
            provider=provider, favorite=True, dry_run=dry_run, music_volume=music_volume
        )
    if re.search(r"\b(fight|hype|workout)\s+song\b", transcript, re.I):
        return sharpedge_play(
            query="fight song",
            provider="spotify",
            dry_run=dry_run,
            music_volume=music_volume,
        )

    query = _play_query(transcript)
    if query:
        return sharpedge_play(
            query=query, provider=provider, dry_run=dry_run, music_volume=music_volume
        )
    return {
        "success": False,
        "message": "heard SharpEdge, but no media command matched",
    }


def _read_volumes() -> dict[str, int]:
    result = _run(["termux-volume"], dry_run=False)
    if not result.get("success"):
        return {}
    try:
        rows = json.loads(result.get("stdout") or "[]")
    except json.JSONDecodeError:
        return {}
    return {row["stream"]: int(row["volume"]) for row in rows if "stream" in row}


def _listen_once(timeout_seconds: int, quiet_beep: bool) -> str:
    saved_volumes = _read_volumes() if quiet_beep else {}
    for stream in BEEP_STREAMS:
        if stream in saved_volumes:
            _run(["termux-volume", stream, "0"], dry_run=False)
    try:
        completed = subprocess.run(
            ["termux-speech-to-text"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise SpeechListenError(
            "termux-speech-to-text is not installed. Install Termux:API."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SpeechListenError("voice listen timed out") from exc
    finally:
        for stream, volume in saved_volumes.items():
            if stream in BEEP_STREAMS:
                _run(["termux-volume", stream, str(volume)], dry_run=False)
    transcript = (completed.stdout or completed.stderr).strip()
    if not transcript:
        raise SpeechListenError("no speech recognized")
    return transcript


def listen_loop(
    dry_run: bool = True,
    timeout_seconds: int = 30,
    quiet_beep: bool = True,
    stop_after_action: bool = False,
    max_listens: int | None = None,
    music_volume: int | None = 12,
    sleep_seconds: float = 1.0,
) -> int:
    print("SharpEdge media router listening. Try: Hey SharpEdge, play my favorite song")
    listens = 0
    while max_listens is None or listens < max_listens:
        listens += 1
        try:
            transcript = _listen_once(timeout_seconds, quiet_beep)
        except SpeechListenError as exc:
            print(f"listen skipped: {exc}")
            time.sleep(sleep_seconds)
            continue
        result = handle_transcript(
            transcript, dry_run=dry_run, music_volume=music_volume
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        if stop_after_action and result.get("success"):
            return 0
        time.sleep(sleep_seconds)
    return 0


def android_media_router_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "state_path": str(STATE_PATH),
        "state": read_state(),
        "commands": {
            "am": _which("am"),
            "input": _which("input"),
            "termux-volume": _which("termux-volume"),
            "termux-speech-to-text": _which("termux-speech-to-text"),
        },
    }


def android_media_router_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {"transcript": "Hey SharpEdge, play my favorite song"},
            {"transcript": "Hey SharpEdge, play my fight song"},
            {
                "transcript": "Hey SharpEdge, play Jack Harlow Tyler Herro remix on YouTube"
            },
            {
                "set_favorite": "SharpEdge, my favorite song is Jack Harlow Tyler Herro remix"
            },
        ],
    }
