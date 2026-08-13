"""SharpEdge read-only live market-state MCP server."""

from __future__ import annotations

from ._common import make_fastmcp


def build_server():
    """Build the freshness-aware SharpEdge market-state server."""
    from code_puppy.plugins.sharpedge_mcp_system.market_state import (
        sharpedge_market_state,
    )

    app = make_fastmcp("SharpEdge Market State Readonly")
    app.tool()(sharpedge_market_state)
    return app


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
