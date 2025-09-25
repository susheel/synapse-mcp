"""Resource registrations for Synapse MCP."""

from typing import Dict, List

from .app import mcp
from .context_helpers import ConnectionAuthError, first_successful_result, require_request_context
from .tools import (
    get_entity,
    get_entity_annotations,
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


__all__ = [
    "get_dataset_annotations",
    "get_dataset_by_id_or_name",
    "get_entity_annotations_resource",
    "get_entity_by_id_or_name",
    "get_file_annotations",
    "get_file_by_id_or_name",
    "get_folder_annotations",
    "get_folder_by_id_or_name",
    "get_project_annotations",
    "get_project_by_id_or_name",
    "get_table_annotations",
    "get_table_by_id_or_name",
]
