"""Bootstrap helpers for the SharpEdge MCP system plugin."""

from __future__ import annotations

from collections.abc import Iterable

from .server_specs import get_server_names, get_server_templates


def list_first_party_servers() -> list[dict[str, str]]:
    """Return compact first-party server metadata for UI/status surfaces."""
    return [
        {
            "id": template.id,
            "name": template.name,
            "display_name": template.display_name,
            "category": template.category,
        }
        for template in get_server_templates()
    ]


def match_first_party_server_names(server_names: Iterable[str]) -> list[str]:
    """Return known SharpEdge server names from an arbitrary sequence."""
    known = set(get_server_names())
    matched = {
        str(server_name).strip()
        for server_name in server_names
        if str(server_name).strip() in known
    }
    return sorted(matched)
