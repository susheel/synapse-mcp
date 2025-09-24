"""Resource registrations for Synapse MCP."""

from typing import Dict, List

from .app import mcp
from .context_helpers import ConnectionAuthError, first_successful_result, require_request_context
from .tools import (
    get_entity,
    get_entity_annotations,
    get_entity_children,
    query_table,
    search_synapse,
)
from .utils import validate_synapse_id


def _search_entities(
    ctx,
    *,
    name: str | None = None,
    entity_type: str | None = None,
    entity_types: List[str] | None = None,
    parent_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, object]]:
    """Run a Synapse search and hydrate the hits into full entity payloads."""
    search_result = search_synapse.fn(
        ctx,
        name=name,
        entity_type=entity_type,
        entity_types=entity_types,
        parent_id=parent_id,
        limit=limit,
        offset=offset,
    )

    if isinstance(search_result, dict) and search_result.get("error"):
        return [search_result]

    hits: List[Dict[str, object]] = search_result.get("hits", []) if isinstance(search_result, dict) else []
    if not hits:
        return []

    entities: List[Dict[str, object]] = []
    seen_ids: set[str] = set()
    for hit in hits:
        entity_id = hit.get("id") if isinstance(hit, dict) else None
        if not entity_id or entity_id in seen_ids:
            continue
        seen_ids.add(entity_id)
        entities.append(get_entity.fn(entity_id, ctx))

    if name:
        normalized = name.lower()
        exact_matches = [
            entity
            for entity in entities
            if isinstance(entity, dict)
            and str(entity.get("name", "")).lower() == normalized
        ]
        return exact_matches

    return entities


@mcp.resource("entities/{id_or_name}")
def get_entity_by_id_or_name(id_or_name: str) -> Dict[str, object]:
    """Get entity by ID or name."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    if validate_synapse_id(id_or_name):
        return get_entity.fn(id_or_name, ctx)

    results = _search_entities(ctx, name=id_or_name, limit=20)
    entity = first_successful_result(results) if results else None
    if entity:
        return entity
    return {"error": f"Entity not found: {id_or_name}"}


@mcp.resource("entities/{id}/annotations")
def get_entity_annotations_resource(id: str) -> Dict[str, object]:
    """Get entity annotations."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    return get_entity_annotations.fn(id, ctx)


@mcp.resource("entities/{id}/children")
def get_entity_children_resource(id: str) -> List[Dict[str, object]]:
    """Get entity children."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return [{"error": str(exc)}]
    return get_entity_children.fn(id, ctx)


@mcp.resource("entities/{entity_type}")
def query_entities_by_type(entity_type: str) -> List[Dict[str, object]]:
    """Query entities by type."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return [{"error": str(exc)}]
    return _search_entities(ctx, entity_type=entity_type, limit=50)


@mcp.resource("entities/parent/{parent_id}")
def query_entities_by_parent(parent_id: str) -> List[Dict[str, object]]:
    """Query entities by parent ID."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return [{"error": str(exc)}]
    return _search_entities(ctx, parent_id=parent_id, limit=50)


@mcp.resource("projects/{id_or_name}")
def get_project_by_id_or_name(id_or_name: str) -> Dict[str, object]:
    """Get project by ID or name."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    if validate_synapse_id(id_or_name):
        entity = get_entity.fn(id_or_name, ctx)
    else:
        results = _search_entities(ctx, name=id_or_name, entity_type="project", limit=20)
        entity = first_successful_result(results) if results else None

    if entity and entity.get("type", "").lower() == "project":
        return entity
    if entity and entity.get("error"):
        return entity
    return {"error": f"Project not found: {id_or_name}"}


@mcp.resource("projects/{id}/annotations")
def get_project_annotations(id: str) -> Dict[str, object]:
    """Get project annotations."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    return get_entity_annotations.fn(id, ctx)


@mcp.resource("projects/{id}/children")
def get_project_children(id: str) -> List[Dict[str, object]]:
    """Get project children."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return [{"error": str(exc)}]
    return get_entity_children.fn(id, ctx)


@mcp.resource("projects/{id}/parent")
def get_project_parent(id: str) -> Dict[str, object]:
    """Get project parent."""
    return {"error": "Projects do not have parents in Synapse"}


@mcp.resource("datasets/{id_or_name}")
def get_dataset_by_id_or_name(id_or_name: str) -> Dict[str, object]:
    """Get dataset by ID or name."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    if validate_synapse_id(id_or_name):
        entity = get_entity.fn(id_or_name, ctx)
    else:
        results = _search_entities(ctx, name=id_or_name, entity_type="dataset", limit=20)
        entity = first_successful_result(results) if results else None

    if entity and entity.get("type", "").lower() == "dataset":
        return entity
    if entity and entity.get("error"):
        return entity
    return {"error": f"Dataset not found: {id_or_name}"}


@mcp.resource("datasets/{id}/annotations")
def get_dataset_annotations(id: str) -> Dict[str, object]:
    """Get dataset annotations."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    return get_entity_annotations.fn(id, ctx)


@mcp.resource("datasets/{id}/children")
def get_dataset_children(id: str) -> List[Dict[str, object]]:
    """Get dataset children."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return [{"error": str(exc)}]
    return get_entity_children.fn(id, ctx)


@mcp.resource("datasets/{id}/parent")
def get_dataset_parent(id: str) -> Dict[str, object]:
    """Get dataset parent."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    entity = get_entity.fn(id, ctx)
    parent_id = entity.get("parentId") if isinstance(entity, dict) else None
    if not parent_id:
        return {"error": "Dataset has no parent"}
    return get_entity.fn(parent_id, ctx)


@mcp.resource("folders/{id_or_name}")
def get_folder_by_id_or_name(id_or_name: str) -> Dict[str, object]:
    """Get folder by ID or name."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    if validate_synapse_id(id_or_name):
        entity = get_entity.fn(id_or_name, ctx)
    else:
        results = _search_entities(ctx, name=id_or_name, entity_type="folder", limit=20)
        entity = first_successful_result(results) if results else None

    if entity and entity.get("type", "").lower() == "folder":
        return entity
    if entity and entity.get("error"):
        return entity
    return {"error": f"Folder not found: {id_or_name}"}


@mcp.resource("folders/{id}/annotations")
def get_folder_annotations(id: str) -> Dict[str, object]:
    """Get folder annotations."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    return get_entity_annotations.fn(id, ctx)


@mcp.resource("folders/{id}/children")
def get_folder_children(id: str) -> List[Dict[str, object]]:
    """Get folder children."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return [{"error": str(exc)}]
    return get_entity_children.fn(id, ctx)


@mcp.resource("folders/{id}/parent")
def get_folder_parent(id: str) -> Dict[str, object]:
    """Get folder parent."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    entity = get_entity.fn(id, ctx)
    parent_id = entity.get("parentId") if isinstance(entity, dict) else None
    if not parent_id:
        return {"error": "Folder has no parent"}
    return get_entity.fn(parent_id, ctx)


@mcp.resource("files/{id_or_name}")
def get_file_by_id_or_name(id_or_name: str) -> Dict[str, object]:
    """Get file by ID or name."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    if validate_synapse_id(id_or_name):
        entity = get_entity.fn(id_or_name, ctx)
    else:
        results = _search_entities(ctx, name=id_or_name, entity_type="file", limit=20)
        entity = first_successful_result(results) if results else None

    if entity and entity.get("type", "").lower() == "file":
        return entity
    if entity and entity.get("error"):
        return entity
    return {"error": f"File not found: {id_or_name}"}


@mcp.resource("files/{id}/annotations")
def get_file_annotations(id: str) -> Dict[str, object]:
    """Get file annotations."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    return get_entity_annotations.fn(id, ctx)


@mcp.resource("files/{id}/children")
def get_file_children(id: str) -> List[Dict[str, object]]:
    """Get file children."""
    return [{"error": "Files do not have children in Synapse"}]


@mcp.resource("files/{id}/parent")
def get_file_parent(id: str) -> Dict[str, object]:
    """Get file parent."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    entity = get_entity.fn(id, ctx)
    parent_id = entity.get("parentId") if isinstance(entity, dict) else None
    if not parent_id:
        return {"error": "File has no parent"}
    return get_entity.fn(parent_id, ctx)


@mcp.resource("tables/{id_or_name}")
def get_table_by_id_or_name(id_or_name: str) -> Dict[str, object]:
    """Get table by ID or name."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    if validate_synapse_id(id_or_name):
        entity = get_entity.fn(id_or_name, ctx)
    else:
        results = _search_entities(ctx, name=id_or_name, entity_type="table", limit=20)
        entity = first_successful_result(results) if results else None

    if entity and entity.get("type", "").lower() == "table":
        return entity
    if entity and entity.get("error"):
        return entity
    return {"error": f"Table not found: {id_or_name}"}


@mcp.resource("tables/{id}/annotations")
def get_table_annotations(id: str) -> Dict[str, object]:
    """Get table annotations."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    return get_entity_annotations.fn(id, ctx)


@mcp.resource("tables/{id}/children")
def get_table_children(id: str) -> List[Dict[str, object]]:
    """Get table children."""
    return [{"error": "Tables do not have children in Synapse"}]


@mcp.resource("tables/{id}/parent")
def get_table_parent(id: str) -> Dict[str, object]:
    """Get table parent."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}
    entity = get_entity.fn(id, ctx)
    parent_id = entity.get("parentId") if isinstance(entity, dict) else None
    if not parent_id:
        return {"error": "Table has no parent"}
    return get_entity.fn(parent_id, ctx)


@mcp.resource("table/{id}/{query}")
def query_table_resource(id: str, query: str) -> Dict[str, object]:
    """Query a table with SQL-like syntax."""
    try:
        ctx = require_request_context()
    except ConnectionAuthError as exc:
        return {"error": str(exc)}

    import urllib.parse

    decoded_query = urllib.parse.unquote(query)
    return query_table.fn(id, decoded_query, ctx)


__all__ = [
    "get_dataset_by_id_or_name",
    "get_dataset_annotations",
    "get_dataset_children",
    "get_dataset_parent",
    "get_entity_annotations_resource",
    "get_entity_by_id_or_name",
    "get_entity_children_resource",
    "get_file_annotations",
    "get_file_by_id_or_name",
    "get_file_children",
    "get_file_parent",
    "get_folder_annotations",
    "get_folder_by_id_or_name",
    "get_folder_children",
    "get_folder_parent",
    "get_project_annotations",
    "get_project_by_id_or_name",
    "get_project_children",
    "get_project_parent",
    "get_table_annotations",
    "get_table_by_id_or_name",
    "get_table_children",
    "get_table_parent",
    "query_entities_by_parent",
    "query_entities_by_type",
    "query_table_resource",
]
