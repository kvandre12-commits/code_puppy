import argparse
import sys
from unittest.mock import AsyncMock, patch

import pytest

from code_puppy.callbacks import clear_callbacks, register_callback


class TestPluginCliArgsMain:
    def setup_method(self):
        clear_callbacks("register_cli_args")
        clear_callbacks("handle_cli_args")

    @pytest.mark.anyio
    async def test_main_short_circuits_with_plugin_exit_code(self):
        from code_puppy.cli_runner import main

        seen = {}

        def add_args(parser):
            parser.add_argument("--bark-report", action="store_true")

        def handle_args(args):
            seen["bark_report"] = args.bark_report
            return {"handled": True, "exit_code": 17}

        register_callback("register_cli_args", add_args)
        register_callback("handle_cli_args", handle_args)

        with (
            patch.object(sys, "argv", ["code-puppy", "--bark-report"]),
            patch(
                "code_puppy.cli_runner.callbacks.on_startup", new_callable=AsyncMock
            ) as mock_startup,
            patch(
                "code_puppy.cli_runner.callbacks.on_shutdown", new_callable=AsyncMock
            ) as mock_shutdown,
        ):
            rc = await main()

        assert rc == 17
        assert seen == {"bark_report": True}
        mock_startup.assert_not_called()
        mock_shutdown.assert_not_called()

    @pytest.mark.anyio
    async def test_main_register_cli_args_fail_fast_on_duplicate_option(self):
        from code_puppy.cli_runner import main

        def add_duplicate(parser):
            parser.add_argument("--prompt")

        register_callback("register_cli_args", add_duplicate)

        with patch.object(sys, "argv", ["code-puppy"]):
            with pytest.raises(argparse.ArgumentError):
                await main()

    @pytest.mark.anyio
    async def test_main_defaults_plugin_exit_code_to_zero(self):
        from code_puppy.cli_runner import main

        def add_args(parser):
            parser.add_argument("--wag", action="store_true")

        def handle_args(args):
            if args.wag:
                return {"handled": True}
            return None

        register_callback("register_cli_args", add_args)
        register_callback("handle_cli_args", handle_args)

        with patch.object(sys, "argv", ["code-puppy", "--wag"]):
            rc = await main()

        assert rc == 0


class TestPluginCliArgsMainEntry:
    def test_main_entry_exits_with_main_return_code(self):
        from code_puppy.cli_runner import main_entry

        def _fake_asyncio_run(coro):
            coro.close()
            return 9

        with (
            patch("asyncio.run", side_effect=_fake_asyncio_run),
            patch("code_puppy.cli_runner.reset_unix_terminal"),
            pytest.raises(SystemExit) as exc_info,
        ):
            main_entry()

        assert exc_info.value.code == 9
