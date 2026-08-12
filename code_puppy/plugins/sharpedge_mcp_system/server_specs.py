"""Catalog specs for SharpEdge first-party MCP servers."""

from __future__ import annotations

from code_puppy.mcp_.server_registry_catalog import (
    MCPServerRequirements,
    MCPServerTemplate,
)

_SERVER_MODULE_PREFIX = "code_puppy.plugins.sharpedge_mcp_system.servers"
_SERVER_REQUIREMENTS = MCPServerRequirements(
    required_tools=["python"],
    system_requirements=[
        "Code Puppy checkout with SharpEdge/DroidPuppy plugins available",
    ],
)


def _python_stdio_template(
    *,
    server_id: str,
    name: str,
    display_name: str,
    description: str,
    module_name: str,
    tags: list[str],
    example_usage: str,
) -> MCPServerTemplate:
    return MCPServerTemplate(
        id=server_id,
        name=name,
        display_name=display_name,
        description=description,
        category="SharpEdge",
        tags=tags,
        type="stdio",
        config={
            "command": "python",
            "args": ["-m", f"{_SERVER_MODULE_PREFIX}.{module_name}"],
            "timeout": 45,
        },
        author="SharpEdge",
        verified=True,
        popular=False,
        requires=_SERVER_REQUIREMENTS,
        example_usage=example_usage,
    )


def get_server_templates() -> list[MCPServerTemplate]:
    """Return first-party SharpEdge MCP server templates.

    These are intentionally thin adapters over existing Code Puppy and
    DroidPuppy capabilities. The servers expose namespaced MCP tools so they
    can coexist with in-process tools without collisions.
    """
    return [
        _python_stdio_template(
            server_id="sharpedge-android-capability",
            name="sharpedge-android-capability",
            display_name="SharpEdge Android Capability",
            description=(
                "First-party Android capability graph and device doctor surface "
                "for SharpEdge/DroidPuppy."
            ),
            module_name="android_capability",
            tags=[
                "sharpedge",
                "android",
                "droidpuppy",
                "capability-graph",
                "device-health",
            ],
            example_usage=(
                "Expose Android capability routing and device health through "
                "namespaced SharpEdge MCP tools."
            ),
        ),
        _python_stdio_template(
            server_id="sharpedge-governance-readonly",
            name="sharpedge-governance-readonly",
            display_name="SharpEdge Governance Readonly",
            description=(
                "First-party governance/status MCP surface for authority, "
                "workflow context, and Project OS health."
            ),
            module_name="governance",
            tags=[
                "sharpedge",
                "governance",
                "authority-gateway",
                "workflow-context",
                "project-os",
            ],
            example_usage=(
                "Expose workflow and authority health without directly minting "
                "leases or performing risky writes."
            ),
        ),
    ]


def get_server_names() -> list[str]:
    """Return just the server names for quick membership checks."""
    return [template.name for template in get_server_templates()]
