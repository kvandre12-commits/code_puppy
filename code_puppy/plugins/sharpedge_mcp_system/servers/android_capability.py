"""SharpEdge Android capability MCP server."""

from __future__ import annotations

from ._common import make_fastmcp


def build_server():
    """Build the first-party Android capability MCP server."""
    from code_puppy.plugins.android_capability_graph_kit.tooling import (
        android_capability_graph,
    )
    from code_puppy.plugins.droidpuppy_doctor.tooling import droidpuppy_doctor

    app = make_fastmcp("SharpEdge Android Capability")

    @app.tool()
    def sharpedge_android_capability_graph(
        deep: bool = False,
        local_port: int = 9222,
    ) -> dict:
        return android_capability_graph(deep=deep, local_port=local_port)

    @app.tool()
    def sharpedge_android_doctor(
        deep: bool = False,
        local_port: int = 9222,
    ) -> dict:
        return droidpuppy_doctor(deep=deep, local_port=local_port)

    return app


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
