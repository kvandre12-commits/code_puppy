"""Tests for the lazy optional-import behavior of ``code_puppy.mcp_``."""

import importlib
import types

import pytest

import code_puppy.mcp_ as mcp_package
from code_puppy.mcp_optional import MCPUnavailableError, has_mcp_support


class TestMCPPackageExports:
    def test_all_exports_defined(self):
        assert hasattr(mcp_package, "__all__")
        assert isinstance(mcp_package.__all__, list)
        assert len(mcp_package.__all__) >= 20

    def test_expected_export_names_present(self):
        expected = {
            "ManagedMCPServer",
            "ServerConfig",
            "ServerState",
            "ServerStatusTracker",
            "Event",
            "MCPManager",
            "ServerInfo",
            "get_mcp_manager",
            "ServerRegistry",
            "MCPErrorIsolator",
            "ErrorStats",
            "ErrorCategory",
            "QuarantinedServerError",
            "get_error_isolator",
            "CircuitBreaker",
            "CircuitState",
            "CircuitOpenError",
            "RetryManager",
            "RetryStats",
            "get_retry_manager",
            "retry_mcp_call",
            "MCPDashboard",
            "MCPConfigWizard",
            "run_add_wizard",
        }
        assert expected.issubset(set(mcp_package.__all__))

    def test_exports_are_accessible_or_raise_friendly_optional_error(self):
        for export_name in mcp_package.__all__:
            if has_mcp_support():
                assert hasattr(mcp_package, export_name), (
                    f"{export_name} not accessible"
                )
                continue

            try:
                getattr(mcp_package, export_name)
            except MCPUnavailableError as exc:
                assert "code-puppy[mcp]" in str(exc)
            else:
                # Log helpers and other non-MCP-backed exports may still load.
                assert hasattr(mcp_package, export_name)

    @pytest.mark.skipif(
        not has_mcp_support(), reason="optional MCP extra not installed"
    )
    def test_core_exports_resolve_when_extra_installed(self):
        for export_name in (
            "ManagedMCPServer",
            "ServerConfig",
            "ServerState",
            "MCPManager",
            "ServerInfo",
            "get_mcp_manager",
            "MCPDashboard",
        ):
            assert hasattr(mcp_package, export_name)


class TestLazyExportImportErrorSeam:
    """Guard the ``__getattr__`` ImportError seam.

    Only a genuine missing-``mcp`` failure (however deeply wrapped) should be
    converted to the friendly ``MCPUnavailableError``; every other import
    failure must propagate untouched.
    """

    _FAKE_MODULE = ".fake_seam_module"
    _FAKE_EXPORT = "_FakeSeamExport"

    @pytest.fixture
    def install_fake_export(self, monkeypatch):
        """Route one throwaway export through a caller-supplied import stub.

        Returns a callable that takes the exception (or module) the stub
        should produce for the fake export and wires up ``importlib`` +
        ``_EXPORTS`` accordingly. Real imports pass through untouched.
        """
        real_import = importlib.import_module

        def _configure(result):
            def fake_import(module_name, package=None):
                if module_name == self._FAKE_MODULE:
                    if isinstance(result, BaseException):
                        raise result
                    return result
                return real_import(module_name, package)

            monkeypatch.setattr(mcp_package.importlib, "import_module", fake_import)
            monkeypatch.setitem(
                mcp_package._EXPORTS, self._FAKE_EXPORT, (self._FAKE_MODULE, "x")
            )

        yield _configure
        # __getattr__ caches successful lookups into module globals; scrub it.
        mcp_package.__dict__.pop(self._FAKE_EXPORT, None)

    @staticmethod
    def _wrapped_missing(module_name):
        """Build an ImportError that wraps a ModuleNotFoundError, pydantic-style."""
        try:
            raise ModuleNotFoundError(
                f"No module named '{module_name}'", name=module_name
            )
        except ModuleNotFoundError as root:
            wrapped = ImportError(
                "Please install the `mcp` package to use the MCP server"
            )
            wrapped.__cause__ = root
            return wrapped

    @pytest.mark.parametrize("missing", ["mcp", "mcp.shared", "mcp.client.session"])
    def test_wrapped_missing_mcp_becomes_unavailable(
        self, install_fake_export, missing
    ):
        install_fake_export(self._wrapped_missing(missing))
        with pytest.raises(MCPUnavailableError) as excinfo:
            getattr(mcp_package, self._FAKE_EXPORT)
        assert "code-puppy[mcp]" in str(excinfo.value)
        assert "uv sync --extra mcp" in str(excinfo.value)

    def test_unrelated_direct_importerror_propagates(self, install_fake_export):
        original = ImportError("totally unrelated import failure")
        install_fake_export(original)
        with pytest.raises(ImportError) as excinfo:
            getattr(mcp_package, self._FAKE_EXPORT)
        assert excinfo.value is original
        assert not isinstance(excinfo.value, MCPUnavailableError)

    def test_unrelated_nested_importerror_propagates(self, install_fake_export):
        install_fake_export(self._wrapped_missing("numpy"))
        with pytest.raises(ImportError) as excinfo:
            getattr(mcp_package, self._FAKE_EXPORT)
        assert not isinstance(excinfo.value, MCPUnavailableError)
        # The original wrapped ImportError propagates unchanged.
        assert isinstance(excinfo.value.__cause__, ModuleNotFoundError)
        assert excinfo.value.__cause__.name == "numpy"

    def test_cyclic_exception_chain_is_safe(self, install_fake_export):
        # A self-referential chain must not hang; and since no node blames
        # ``mcp`` it must propagate unchanged.
        err = ImportError("self referential")
        err.__cause__ = err
        install_fake_export(err)
        with pytest.raises(ImportError) as excinfo:
            getattr(mcp_package, self._FAKE_EXPORT)
        assert not isinstance(excinfo.value, MCPUnavailableError)

    def test_successful_export_is_returned_and_cached(self, install_fake_export):
        sentinel = object()
        install_fake_export(types.SimpleNamespace(x=sentinel))
        assert getattr(mcp_package, self._FAKE_EXPORT) is sentinel
        # Resolved exports are memoized on the module for subsequent access.
        assert mcp_package.__dict__.get(self._FAKE_EXPORT) is sentinel
