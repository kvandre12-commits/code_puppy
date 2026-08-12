"""Tests for ModelFactory config caching and invalidation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from code_puppy import callbacks
from code_puppy import config as cp_config
from code_puppy.model_factory import ModelFactory


class TestModelFactoryConfigCache(unittest.TestCase):
    def setUp(self):
        ModelFactory.clear_config_cache()

    def tearDown(self):
        ModelFactory.clear_config_cache()

    def _patch_model_sources(self, temp_dir: str):
        temp_root = Path(temp_dir)
        bundle_dir = temp_root / "bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "fake_model_factory.py").write_text(
            "# test shim\n", encoding="utf-8"
        )
        bundled_payload = json.dumps(
            {"bundled-model": {"type": "openai", "name": "gpt-test"}}
        )
        (bundle_dir / "models.json").write_text(
            bundled_payload,
            encoding="utf-8",
        )
        (bundle_dir / "models_minimal.json").write_text(
            bundled_payload,
            encoding="utf-8",
        )

        missing = str(temp_root / "missing.json")
        return (
            patch.multiple(
                "code_puppy.config",
                CHATGPT_MODELS_FILE=missing,
                CLAUDE_MODELS_FILE=missing,
                GEMINI_MODELS_FILE=missing,
                COPILOT_MODELS_FILE=missing,
            ),
            patch(
                "code_puppy.model_factory.__file__",
                str(bundle_dir / "fake_model_factory.py"),
            ),
            patch("code_puppy.model_factory.EXTRA_MODELS_FILE", missing),
        )

    def test_load_config_reuses_cached_merge_but_returns_fresh_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_patch, file_patch, extra_patch = self._patch_model_sources(temp_dir)
            with config_patch, file_patch, extra_patch:
                with patch(
                    "code_puppy.model_factory.json.load", wraps=json.load
                ) as mock_load:
                    first = ModelFactory.load_config()
                    cold_load_calls = mock_load.call_count
                    second = ModelFactory.load_config()

                self.assertGreaterEqual(cold_load_calls, 1)
                self.assertEqual(mock_load.call_count, cold_load_calls)
                self.assertIsNot(first, second)
                first["bundled-model"]["name"] = "mutated"

                third = ModelFactory.load_config()
                self.assertEqual(third["bundled-model"]["name"], "gpt-test")

    def test_load_config_invalidates_when_callback_set_changes(self):
        def plugin_models():
            return {"plugin-model": {"type": "openai", "name": "gpt-plugin"}}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_patch, file_patch, extra_patch = self._patch_model_sources(temp_dir)
            with config_patch, file_patch, extra_patch:
                callbacks.unregister_callback("load_models_config", plugin_models)
                base = ModelFactory.load_config()
                self.assertNotIn("plugin-model", base)

                callbacks.register_callback("load_models_config", plugin_models)
                try:
                    refreshed = ModelFactory.load_config()
                finally:
                    callbacks.unregister_callback("load_models_config", plugin_models)

                self.assertIn("plugin-model", refreshed)

    def test_load_config_uses_runtime_selected_bundled_models_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            minimal_models = temp_root / "models_minimal.json"
            minimal_models.write_text(
                json.dumps(
                    {
                        "tiny-model": {
                            "type": "gemini",
                            "name": "tiny-model",
                        }
                    }
                ),
                encoding="utf-8",
            )
            missing = str(temp_root / "missing.json")

            with (
                patch.multiple(
                    "code_puppy.config",
                    CHATGPT_MODELS_FILE=missing,
                    CLAUDE_MODELS_FILE=missing,
                    GEMINI_MODELS_FILE=missing,
                    COPILOT_MODELS_FILE=missing,
                ),
                patch("code_puppy.model_factory.EXTRA_MODELS_FILE", missing),
                patch(
                    "code_puppy.model_factory.bundled_models_path",
                    return_value=minimal_models,
                ),
            ):
                config = ModelFactory.load_config()

            self.assertIn("tiny-model", config)
            self.assertEqual(config["tiny-model"]["name"], "tiny-model")

    def test_clear_model_cache_clears_model_factory_cache(self):
        with patch.object(ModelFactory, "clear_config_cache") as mock_clear:
            cp_config.clear_model_cache()
        mock_clear.assert_called_once_with()
