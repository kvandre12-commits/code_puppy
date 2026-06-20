from __future__ import annotations

import json
import sys
from pathlib import Path

from code_puppy.plugins.android_media_router import __main__ as main_mod
from code_puppy.plugins.android_media_router import register_callbacks, tooling


class TestMediaRouterTooling:
    def test_set_favorite_dry_run_does_not_write_state(self, monkeypatch, tmp_path):
        state_path = tmp_path / "sharpedge_media.json"
        legacy_path = tmp_path / "favorite.txt"
        monkeypatch.setattr(tooling, "STATE_PATH", state_path)
        monkeypatch.setattr(tooling, "LEGACY_FAVORITE_PATH", legacy_path)

        result = tooling.set_favorite(
            "Jack Harlow Tyler Herro remix", provider="youtube", dry_run=True
        )

        assert result["success"] is True
        assert result["favorite_provider"] == "youtube"
        assert result["favorite_target"] == "Jack Harlow Tyler Herro remix"
        assert not state_path.exists()
        assert not legacy_path.exists()

    def test_set_favorite_execute_writes_state_and_legacy_file(
        self, monkeypatch, tmp_path
    ):
        state_path = tmp_path / "sharpedge_media.json"
        legacy_path = tmp_path / "favorite.txt"
        monkeypatch.setattr(tooling, "STATE_PATH", state_path)
        monkeypatch.setattr(tooling, "LEGACY_FAVORITE_PATH", legacy_path)

        tooling.set_favorite(
            "https://www.youtube.com/watch?v=mprOwA6wp3o",
            provider="youtube",
            dry_run=False,
        )

        state = json.loads(state_path.read_text())
        assert state == {
            "favorite_provider": "youtube",
            "favorite_target": "https://www.youtube.com/watch?v=mprOwA6wp3o",
        }
        assert (
            legacy_path.read_text().strip()
            == "https://www.youtube.com/watch?v=mprOwA6wp3o"
        )

    def test_sharpedge_play_routes_fight_song_to_spotify(self):
        result = tooling.sharpedge_play(
            query="fight song",
            provider="auto",
            dry_run=True,
            press_play=True,
        )

        assert result["success"] is True
        assert result["provider"] == "spotify"
        assert result["target"] == tooling.FIGHT_SONG_URI
        assert result["label"] == tooling.FIGHT_SONG_LABEL
        assert result["command"][0:4] == [
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
        ]
        assert result["actions"][-1]["name"] == "press_media_play_skipped"

    def test_handle_transcript_sets_favorite_from_voice(self, monkeypatch, tmp_path):
        state_path = tmp_path / "sharpedge_media.json"
        monkeypatch.setattr(tooling, "STATE_PATH", state_path)
        monkeypatch.setattr(tooling, "LEGACY_FAVORITE_PATH", tmp_path / "favorite.txt")

        result = tooling.handle_transcript(
            "Hey SharpEdge my favorite song is Tyler Herro remix on YouTube",
            dry_run=True,
        )

        assert result["success"] is True
        assert result["favorite_provider"] == "youtube"
        assert result["favorite_target"] == "Tyler Herro remix on YouTube"

    def test_handle_transcript_plays_favorite(self, monkeypatch, tmp_path):
        state_path = tmp_path / "sharpedge_media.json"
        state_path.write_text(
            json.dumps(
                {
                    "favorite_provider": "youtube",
                    "favorite_target": "Jack Harlow Tyler Herro remix",
                }
            )
        )
        monkeypatch.setattr(tooling, "STATE_PATH", state_path)
        monkeypatch.setattr(tooling, "LEGACY_FAVORITE_PATH", tmp_path / "favorite.txt")

        result = tooling.handle_transcript(
            "Hey SharpEdge, play my favorite song",
            dry_run=True,
            music_volume=9,
        )

        assert result["success"] is True
        assert result["provider"] == "youtube"
        assert result["target"] == "Jack Harlow Tyler Herro remix"
        assert result["actions"][0]["name"] == "set_music_volume"
        assert result["actions"][0]["result"]["args"] == ["termux-volume", "music", "9"]

    def test_handle_transcript_ignores_missing_wake_word(self):
        result = tooling.handle_transcript("play my favorite song", dry_run=True)
        assert result == {
            "success": False,
            "ignored": True,
            "message": "wake word 'SharpEdge' not heard",
        }

    def test_doctor_and_examples_are_shaped(self, monkeypatch):
        monkeypatch.setattr(tooling, "STATE_PATH", Path("/tmp/sharpedge_media.json"))
        doctor = tooling.android_media_router_doctor()
        examples = tooling.android_media_router_examples()

        assert doctor["success"] is True
        assert "commands" in doctor
        assert examples["success"] is True
        assert any("favorite song" in str(row).lower() for row in examples["examples"])


class TestMediaRouterCli:
    def test_main_routes_transcript_and_exits_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(
            main_mod,
            "handle_transcript",
            lambda transcript, dry_run, music_volume: {
                "success": True,
                "transcript": transcript,
                "dry_run": dry_run,
                "music_volume": music_volume,
            },
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["sharpedge-media", "--say", "Hey SharpEdge play my favorite song"],
        )

        try:
            main_mod.main()
        except SystemExit as exc:
            assert exc.code == 0

        output = json.loads(capsys.readouterr().out)
        assert output["success"] is True
        assert output["dry_run"] is True
        assert output["transcript"] == "Hey SharpEdge play my favorite song"

    def test_main_execute_mode_disables_dry_run(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_set_favorite(target: str, provider: str, dry_run: bool):
            captured.update(
                {"target": target, "provider": provider, "dry_run": dry_run}
            )
            return {"success": True}

        monkeypatch.setattr(main_mod, "set_favorite", fake_set_favorite)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "sharpedge-media",
                "--set-favorite",
                "fight song",
                "--provider",
                "spotify",
                "--execute",
            ],
        )

        try:
            main_mod.main()
        except SystemExit as exc:
            assert exc.code == 0

        assert captured == {
            "target": "fight song",
            "provider": "spotify",
            "dry_run": False,
        }

    def test_main_loop_exits_with_listen_loop_code(self, monkeypatch):
        monkeypatch.setattr(main_mod, "listen_loop", lambda **kwargs: 7)
        monkeypatch.setattr(sys, "argv", ["sharpedge-media", "--loop"])

        try:
            main_mod.main()
        except SystemExit as exc:
            assert exc.code == 7


class TestMediaRouterPluginRegistration:
    def test_register_tools_callback_exposes_full_surface(self):
        specs = register_callbacks.register_tools_callback()
        names = {spec["name"] for spec in specs}
        assert names == {
            "android_media_router_doctor",
            "sharpedge_play",
            "sharpedge_media_handle_transcript",
            "sharpedge_media_set_favorite",
            "android_media_router_examples",
        }

    def test_register_agent_tools_advertises_same_surface(self):
        advertised = register_callbacks._advertise_tools_to_agent("code-puppy")
        assert advertised == [
            "android_media_router_doctor",
            "sharpedge_play",
            "sharpedge_media_handle_transcript",
            "sharpedge_media_set_favorite",
            "android_media_router_examples",
        ]
