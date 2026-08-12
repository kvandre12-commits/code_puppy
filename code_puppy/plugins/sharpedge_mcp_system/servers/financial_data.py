"""SharpEdge read-only financial-data MCP server."""

from __future__ import annotations

from ._common import make_fastmcp


def build_server():
    """Build the first-party SEC/EDGAR financial-data server."""
    from code_puppy.plugins.sec_edgar.tooling import (
        sec_edgar_company_facts,
        sec_edgar_company_profile,
        sec_edgar_recent_filings,
    )

    app = make_fastmcp("SharpEdge Financial Data Readonly")
    app.tool()(sec_edgar_company_profile)
    app.tool()(sec_edgar_recent_filings)
    app.tool()(sec_edgar_company_facts)
    return app


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
