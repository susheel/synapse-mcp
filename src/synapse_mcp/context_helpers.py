"""Helpers for accessing request-scoped context and Synapse operations."""

from typing import Any, Dict, List, Optional

from fastmcp import Context
from fastmcp.server.context import request_ctx

from .connection_auth import ConnectionAuthError, get_synapse_client
from .entities import (
    BaseEntityOperations,
    DatasetOperations,
    FileOperations,
    FolderOperations,
    ProjectOperations,
    TableOperations,
)
from .query import QueryBuilder


def get_request_context() -> Optional[Context]:
    """Return the request-scoped FastMCP context if available."""
    try:
        return request_ctx.get()
    except LookupError:
        return None


def require_request_context() -> Context:
    """Fetch the active request context or raise an auth error."""
    ctx = get_request_context()
    if ctx is None:
        raise ConnectionAuthError(
            "No active request context; ensure the request is routed through an authenticated MCP connection."
        )
    return ctx


def first_successful_result(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the first non-error result from a list of entity responses."""
    for item in results:
        if not isinstance(item, dict):
            return item
        if not item.get("error"):
            return item
    return None


def get_entity_operations(ctx: Context) -> Dict[str, Any]:
    """Get entity operations for this connection's synapseclient."""
    synapse_client = get_synapse_client(ctx)

    entity_ops = ctx.get_state("entity_ops")
    if entity_ops:
        return entity_ops

    entity_ops = {
        "base": BaseEntityOperations(synapse_client),
        "project": ProjectOperations(synapse_client),
        "folder": FolderOperations(synapse_client),
        "file": FileOperations(synapse_client),
        "table": TableOperations(synapse_client),
        "dataset": DatasetOperations(synapse_client),
    }

    ctx.set_state("entity_ops", entity_ops)
    return entity_ops


def get_query_builder(ctx: Context) -> QueryBuilder:
    """Get query builder for this connection's synapseclient."""
    synapse_client = get_synapse_client(ctx)

    query_builder = ctx.get_state("query_builder")
    if query_builder:
        return query_builder

    query_builder = QueryBuilder(synapse_client)
    ctx.set_state("query_builder", query_builder)
    return query_builder


__all__ = [
    "ConnectionAuthError",
    "first_successful_result",
    "get_entity_operations",
    "get_query_builder",
    "get_request_context",
    "require_request_context",
]
