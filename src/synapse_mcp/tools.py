"""Tool registrations for Synapse MCP."""

import json
from typing import Any, Dict, List, Optional

from fastmcp import Context

from .app import mcp
from .connection_auth import get_synapse_client
from .context_helpers import ConnectionAuthError, get_entity_operations
from .utils import format_annotations, validate_synapse_id


DEFAULT_RETURN_FIELDS: List[str] = ["name", "description", "node_type"]


def _normalize_fields(fields: Optional[List[str]]) -> List[str]:
    """Deduplicate and strip return field entries while preserving order."""
    if not fields:
        return []

    seen: set[str] = set()
    normalized: List[str] = []
    for raw in fields:
        cleaned = str(raw).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


@mcp.tool()
def get_entity(entity_id: str, ctx: Context) -> Dict[str, Any]:
    """Get a Synapse entity by ID."""
    if not validate_synapse_id(entity_id):
        return {"error": f"Invalid Synapse ID: {entity_id}"}

    try:
        entity_ops = get_entity_operations(ctx)
        return entity_ops["base"].get_entity_by_id(entity_id)
    except ConnectionAuthError as exc:
        return {"error": f"Authentication required: {exc}", "entity_id": entity_id}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"error": str(exc), "entity_id": entity_id}


@mcp.tool()
def get_entity_annotations(entity_id: str, ctx: Context) -> Dict[str, Any]:
    """Get annotations for an entity."""
    if not validate_synapse_id(entity_id):
        return {"error": f"Invalid Synapse ID: {entity_id}"}

    try:
        entity_ops = get_entity_operations(ctx)
        annotations = entity_ops["base"].get_entity_annotations(entity_id)
        return format_annotations(annotations)
    except ConnectionAuthError as exc:
        return {"error": f"Authentication required: {exc}", "entity_id": entity_id}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"error": str(exc), "entity_id": entity_id}


@mcp.tool()
def get_entity_children(entity_id: str, ctx: Context) -> List[Dict[str, Any]]:
    """Get child entities of a container entity."""
    if not validate_synapse_id(entity_id):
        return [{"error": f"Invalid Synapse ID: {entity_id}"}]

    try:
        entity_ops = get_entity_operations(ctx)
        entity = entity_ops["base"].get_entity_by_id(entity_id)
        entity_type = entity.get("type", "").lower()

        if entity_type == "project":
            return entity_ops["project"].get_project_children(entity_id)
        if entity_type == "folder":
            return entity_ops["folder"].get_folder_children(entity_id)
        return [{"error": f"Entity {entity_id} is not a container entity"}]
    except ConnectionAuthError as exc:
        return [{"error": f"Authentication required: {exc}", "entity_id": entity_id}]
    except Exception as exc:  # pragma: no cover - defensive path
        return [{"error": str(exc), "entity_id": entity_id}]


@mcp.tool()
def search_synapse(
    ctx: Context,
    query_term: Optional[str] = None,
    name: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_types: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Execute a Synapse search using the public search endpoint."""
    try:
        synapse_client = get_synapse_client(ctx)
    except ConnectionAuthError as exc:
        return {"error": f"Authentication required: {exc}"}

    sanitized_limit = max(0, min(limit, 100))
    sanitized_offset = max(0, offset)

    query_terms: List[str] = []
    if query_term:
        query_terms.append(query_term)
    if name and name not in query_terms:
        query_terms.append(name)

    default_return_fields = _normalize_fields(DEFAULT_RETURN_FIELDS)
    request_payload: Dict[str, Any] = {
        "queryTerm": query_terms,
        "start": sanitized_offset,
        "size": sanitized_limit,
    }

    normalized_fields = default_return_fields
    if normalized_fields:
        request_payload["returnFields"] = normalized_fields

    requested_types: List[str] = []
    if entity_types:
        requested_types.extend(entity_types)
    if entity_type:
        requested_types.append(entity_type)

    boolean_query: List[Dict[str, Any]] = []
    for item in requested_types:
        normalized = (item or "").strip().lower()
        if not normalized:
            continue
        boolean_query.append({"key": "node_type", "value": normalized})

    if parent_id:
        boolean_query.append({"key": "path", "value": parent_id})

    if boolean_query:
        request_payload["booleanQuery"] = boolean_query

    warnings: List[str] = []
    original_payload: Optional[Dict[str, Any]] = None
    dropped_return_fields: Optional[List[str]] = None

    try:
        response = synapse_client.restPOST("/search", body=json.dumps(request_payload))
    except ConnectionAuthError as exc:
        return {"error": f"Authentication required: {exc}"}
    except Exception as exc:  # pragma: no cover - defensive path
        error_message = str(exc)
        if "Invalid field name" in error_message and "returnFields" in request_payload:
            original_payload = dict(request_payload)
            dropped_return_fields = list(request_payload.get("returnFields", []))
            fallback_payload = {k: v for k, v in request_payload.items() if k != "returnFields"}

            try:
                response = synapse_client.restPOST("/search", body=json.dumps(fallback_payload))
            except Exception as fallback_exc:  # pragma: no cover - defensive path
                return {
                    "error": str(fallback_exc),
                    "query": fallback_payload,
                    "original_query": original_payload,
                    "dropped_return_fields": dropped_return_fields,
                }

            warnings.append(
                f"Synapse rejected requested return fields {dropped_return_fields}; retried without custom return fields."
            )
            request_payload = fallback_payload
        else:
            return {"error": error_message, "query": request_payload}

    result: Dict[str, Any] = {
        "found": response.get("found", 0),
        "start": response.get("start", sanitized_offset),
        "hits": response.get("hits", []),
        "facets": response.get("facets", []),
        "query": request_payload,
    }

    if warnings:
        result["warnings"] = warnings
    if original_payload:
        result["original_query"] = original_payload
    if dropped_return_fields:
        result["dropped_return_fields"] = dropped_return_fields

    return result


@mcp.tool()
def query_table(table_id: str, query: str, ctx: Context) -> Dict[str, Any]:
    """Query a Synapse table."""
    if not validate_synapse_id(table_id):
        return {"error": f"Invalid Synapse ID: {table_id}"}

    try:
        entity_ops = get_entity_operations(ctx)
        return entity_ops["table"].query_table(table_id, query)
    except ConnectionAuthError as exc:
        return {"error": f"Authentication required: {exc}", "table_id": table_id}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"error": str(exc), "table_id": table_id, "query": query}


__all__ = [
    "get_entity",
    "get_entity_annotations",
    "get_entity_children",
    "query_table",
    "search_synapse",
]
