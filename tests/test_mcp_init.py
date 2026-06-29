"""Tests for the lazy optional-import behavior of ``code_puppy.mcp_``."""

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
