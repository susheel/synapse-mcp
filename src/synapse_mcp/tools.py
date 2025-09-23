"""Tool registrations for Synapse MCP."""

from typing import Any, Dict, List, Optional

from fastmcp import Context

from .app import mcp
from .context_helpers import ConnectionAuthError, get_entity_operations, get_query_builder
from .entities.croissant import convert_to_croissant
from .utils import format_annotations, validate_synapse_id


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
def search_entities(
    search_term: str,
    ctx: Context,
    entity_type: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for Synapse entities."""
    params = {"name": search_term}
    if entity_type:
        params["entity_type"] = entity_type
    if parent_id:
        params["parent_id"] = parent_id
    return query_entities(ctx, **params)


@mcp.tool()
def query_entities(
    ctx: Context,
    entity_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    name: Optional[str] = None,
    annotations: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query entities based on various criteria."""
    try:
        query_builder = get_query_builder(ctx)
        import json

        params: Dict[str, Any] = {}
        if entity_type:
            params["entity_type"] = entity_type
        if parent_id:
            params["parent_id"] = parent_id
        if name:
            params["name"] = name
        if annotations:
            params["annotations"] = json.loads(annotations)

        query = query_builder.build_combined_query(params)
        return query_builder.execute_query(query)
    except ConnectionAuthError as exc:
        return [{"error": f"Authentication required: {exc}"}]
    except Exception as exc:
        error_params = {
            "entity_type": entity_type,
            "parent_id": parent_id,
            "name": name,
            "annotations": annotations,
        }
        sanitized_params = {key: value for key, value in error_params.items() if value is not None}
        return [{"error": str(exc), "params": sanitized_params}]


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


@mcp.tool()
def get_datasets_as_croissant(ctx: Context) -> Dict[str, Any]:
    """Get public datasets in Croissant metadata format."""
    table_id = "syn61609402"
    query_result = query_table.fn(table_id, f"SELECT * FROM {table_id}", ctx)
    if "error" in query_result:
        return query_result
    return convert_to_croissant(query_result)


__all__ = [
    "get_datasets_as_croissant",
    "get_entity",
    "get_entity_annotations",
    "get_entity_children",
    "query_entities",
    "query_table",
    "search_entities",
]
