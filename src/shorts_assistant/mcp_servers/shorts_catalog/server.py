"""MCP stdio server for shorts_catalog (FastMCP)."""

from __future__ import annotations

from typing import Any

from .catalog import CatalogService
from .schemas import GetShortArgs, ListRecentShortsArgs, SearchShortsArgs

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "mcp package required for shorts_catalog server. pip install 'mcp>=1.2'"
    ) from exc

mcp = FastMCP("shorts_catalog")
_catalog = CatalogService()


@mcp.tool()
def list_recent_shorts(limit: int = 5) -> dict[str, Any]:
    """List recent successful Shorts topics and scores (read-only)."""
    args = ListRecentShortsArgs(limit=limit)
    return _catalog.list_recent_shorts(limit=args.limit)


@mcp.tool()
def search_shorts(query: str, limit: int = 5) -> dict[str, Any]:
    """Search catalog by topic/hook keyword (read-only)."""
    args = SearchShortsArgs(query=query, limit=limit)
    return _catalog.search_shorts(query=args.query, limit=args.limit)


@mcp.tool()
def get_short(execution_id: str) -> dict[str, Any]:
    """Get one Short by execution UUID (read-only summary)."""
    args = GetShortArgs(execution_id=execution_id)
    return _catalog.get_short(execution_id=str(args.execution_id))


@mcp.resource("catalog://stats")
def catalog_stats() -> str:
    """Counts of stored catalog rows."""
    import json

    return json.dumps(_catalog.stats())


def main() -> None:
    """Purpose: stdio entrypoint for MCP clients."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
