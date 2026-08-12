"""SharpEdge governance/status MCP server."""

from __future__ import annotations

from ._common import make_fastmcp


def build_server():
    """Build the first-party governance/status MCP server."""
    from code_puppy.plugins.authority_gateway.tooling import authority_gateway_status
    from code_puppy.plugins.droidpuppy_context_kit.tooling import (
        droidpuppy_context_doctor,
    )
    from code_puppy.plugins.project_os_supervisor.tooling import (
        project_os_bus_status,
        project_os_supervisor_status,
    )

    app = make_fastmcp("SharpEdge Governance Readonly")

    @app.tool()
    def sharpedge_authority_gateway_status() -> dict:
        return authority_gateway_status()

    @app.tool()
    def sharpedge_droidpuppy_context_doctor(root: str = "") -> dict:
        return droidpuppy_context_doctor(root=root)

    @app.tool()
    def sharpedge_project_os_bus_status(timeout_seconds: float = 0.5) -> dict:
        return project_os_bus_status(timeout_seconds=timeout_seconds)

    @app.tool()
    def sharpedge_project_os_supervisor_status(
        manifest_path: str = "",
        service_name: str = "",
    ) -> dict:
        return project_os_supervisor_status(
            manifest_path=manifest_path,
            service_name=service_name,
        )

    return app


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
