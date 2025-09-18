#!/usr/bin/env python3
"""
Script to run the Synapse MCP server with SSE support.
"""

import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

from synapse_mcp import mcp, get_entity, get_entity_annotations, get_entity_children, search_entities, get_datasets_as_croissant, query_entities, query_table

from synapse_mcp.auth_server import require_mcp_auth, auth_routes
from synapse_mcp import pat_auth_manager

# --- Main Application Setup ---
# Start with the pre-configured app from the FastMCP library.
app = mcp.streamable_http_app()

# Add the custom OAuth routes to the main application's router.
app.router.routes.extend(auth_routes)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server info endpoint
@mcp.custom_route("/info", methods=["GET"])
async def get_info():
    """Get server info."""
    return {
        "name": "Synapse MCP Server",
        "description": "The MCP server for working with the Synapse repository.",
        "url": os.environ.get("MCP_SERVER_URL", f"mcp://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('PORT', '9000')}") + "/mcp",
        "oauth_enabled": True,
        "version": "0.1.0"
    }

@mcp.custom_route("/tools", methods=["GET"])
async def list_tools():
    """List available tools."""
    return [
        {
            "name": "get_entity",
            "description": "Get an entity by ID"
        },
        {
            "name": "get_entity_annotations",
            "description": "Get annotations for an entity"
        },
        {
            "name": "get_entity_children",
            "description": "Get child entities of a container entity"
        },
        {
            "name": "search_entities",
            "description": "Search for a Synpase entity"
        },
        {
            "name": "query_entities",
            "description": "Query entities based on various criteria"
        },
        {
            "name": "query_table",
            "description": "Query a Synapse table"
        },
        {
            "name": "get_datasets_as_croissant",
            "description": "Get public datasets in Croissant metadata format"
        }
    ]

@mcp.custom_route("/resources", methods=["GET"])
async def list_resources():
    """List available resources."""
    return [
        {
            "pattern": "entities/{id_or_name}",
            "description": "Get entity by ID or name"
        },
        {
            "pattern": "entities/{id}/annotations",
            "description": "Get entity annotations"
        },
        {
            "pattern": "entities/{id}/children",
            "description": "Get entity children"
        },
        {
            "pattern": "entities/{entity_type}",
            "description": "Query entities by type"
        },
        {
            "pattern": "entities/parent/{parent_id}",
            "description": "Query entities by parent ID"
        },
        {
            "pattern": "projects/{id_or_name}",
            "description": "Get project by ID or name"
        },
        {
            "pattern": "projects/{id}/annotations",
            "description": "Get project annotations"
        },
        {
            "pattern": "projects/{id}/children",
            "description": "Get project children"
        },
        {
            "pattern": "projects/{id}/parent",
            "description": "Get project parent"
        },
        {
            "pattern": "datasets/{id_or_name}",
            "description": "Get datasets by ID or Name"
        },
        {
            "pattern": "datasets/{id}/annotations",
            "description": "Get datasets annotations"
        },
        {
            "pattern": "datasets/{id}/children",
            "description": "Get datasets children"
        },
        {
            "pattern": "datasets/{id}/parent",
            "description": "Get datasets parent"
        },
        {
            "pattern": "folders/{id_or_name}",
            "description": "Get folder by ID or name"
        },
        {
            "pattern": "folders/{id}/annotations",
            "description": "Get folders annotations"
        },
        {
            "pattern": "folders/{id}/children",
            "description": "Get folders children"
        },
        {
            "pattern": "folders/{id}/parent",
            "description": "Get datasets parent"
        },
        {
            "pattern": "files/{id_or-name}",
            "description": "Get file by ID or Name"
        },
        {
            "pattern": "files/{id}/annotations",
            "description": "Get file annotations"
        },
        {
            "pattern": "files/{id}/children",
            "description": "Get file children"
        },
        {
            "pattern": "files/{id}/parent",
            "description": "Get file parent"
        },
        {
            "pattern": "tables/{id_or-name}",
            "description": "Get table by ID or Name"
        },
        {
            "pattern": "tables/{id}/annotations",
            "description": "Get table annotations"
        },
        {
            "pattern": "tables/{id}/children",
            "description": "Get table children"
        },
        {
            "pattern": "tables/{id}/parent",
            "description": "Get table parent"
        },
        {
            "pattern": "table/{id}/{query}",
            "description": "Query a table with SQL-like syntax"
        }
    ]


@mcp.custom_route("/tools/get_entity", methods=["POST"])
async def tool_get_entity(request: Request, user: dict = Depends(require_mcp_auth)):
    """Get an entity by ID."""
    data = await request.json()
    return get_entity(**data)

@mcp.custom_route("/tools/get_entity_annotations", methods=["POST"])
async def tool_get_entity_annotations(request: Request, user: dict = Depends(require_mcp_auth)):
    """Get annotations for an entity."""
    data = await request.json()
    return get_entity_annotations(**data)

@mcp.custom_route("/tools/get_entity_children", methods=["POST"])
async def tool_get_entity_children(request: Request, user: dict = Depends(require_mcp_auth)):
    """Get child entities of a container entity."""
    data = await request.json()
    return get_entity_children(**data)

@mcp.custom_route("/tools/search_entities", methods=["POST"])
async def tool_search_entities(request: Request, user: dict = Depends(require_mcp_auth)):
    """Search for Synapse entities."""
    data = await request.json()
    return search_entities(**data)


@mcp.custom_route("/tools/query_entities", methods=["POST"])
async def tool_query_entities(request: Request, user: dict = Depends(require_mcp_auth)):
    """Query entities based on various criteria."""
    data = await request.json()
    return query_entities(**data)

@mcp.custom_route("/tools/query_table", methods=["POST"])
async def tool_query_table(request: Request, user: dict = Depends(require_mcp_auth)):
    """Query a Synapse table."""
    data = await request.json()
    return query_table(**data)

@mcp.custom_route("/tools/get_datasets_as_croissant", methods=["POST"])
async def tool_get_datasets_as_croissant(request: Request, user: dict = Depends(require_mcp_auth)):
    """Get public datasets in Croissant metadata format."""
    data = await request.json()
    return get_datasets_as_croissant(**data)

# Resource endpoints
@mcp.custom_route("/resources/entities/{id_or_name}", methods=["GET"])
async def resource_get_entity(id_or_name: str, user: dict = Depends(require_mcp_auth)):
    """Get entity by ID or name."""
    from synapse_mcp import get_entity_by_id_or_name
    return get_entity_by_id_or_name(id_or_name)

@mcp.custom_route("/resources/entities/{id}/annotations", methods=["GET"])
async def resource_get_entity_annotations(id: str, user: dict = Depends(require_mcp_auth)):
    """Get entity annotations."""
    return get_entity_annotations(entity_id=id)

@mcp.custom_route("/resources/entities/{id}/children", methods=["GET"])
async def resource_get_entity_children(id: str, user: dict = Depends(require_mcp_auth)):
    """Get entity children."""
    return get_entity_children(entity_id=id)    

@mcp.custom_route("/resources/entities/{entity_type}", methods=["GET"])
async def resource_query_entities_by_type(entity_type: str, user: dict = Depends(require_mcp_auth)):
    """Query entities by type."""
    return query_entities(entity_type=entity_type)

@mcp.custom_route("/resources/entities/parent/{parent_id}", methods=["GET"])
async def resource_query_entities_by_parent(parent_id: str, user: dict = Depends(require_mcp_auth)):
    """Query entities by parent ID."""
    return query_entities(parent_id=parent_id)

# Project resources
@mcp.custom_route("/resources/projects/{id_or_name}", methods=["GET"])
async def resource_get_project(id_or_name: str, user: dict = Depends(require_mcp_auth)):
    """Get project by ID or name."""
    from synapse_mcp import get_project_by_id_or_name
    return get_project_by_id_or_name(id_or_name)

@mcp.custom_route("/resources/projects/{id}/annotations", methods=["GET"])
async def resource_get_project_annotations(id: str, user: dict = Depends(require_mcp_auth)):
    """Get project annotations."""
    return get_entity_annotations(entity_id=id)

@mcp.custom_route("/resources/projects/{id}/children", methods=["GET"])
async def resource_get_project_children(id: str, user: dict = Depends(require_mcp_auth)):
    """Get project children."""
    return get_entity_children(entity_id=id)

@mcp.custom_route("/resources/projects/{id}/parent", methods=["GET"])
async def resource_get_project_parent(id: str, user: dict = Depends(require_mcp_auth)):
    """Get project parent."""
    from synapse_mcp import get_project_parent
    return get_project_parent(id)

# Dataset resources
@mcp.custom_route("/resources/datasets/{id_or_name}", methods=["GET"])
async def resource_get_dataset(id_or_name: str, user: dict = Depends(require_mcp_auth)):
    """Get dataset by ID or name."""
    from synapse_mcp import get_dataset_by_id_or_name
    return get_dataset_by_id_or_name(id_or_name)

@mcp.custom_route("/resources/datasets/{id}/annotations", methods=["GET"])
async def resource_get_dataset_annotations(id: str, user: dict = Depends(require_mcp_auth)):
    """Get dataset annotations."""    
    return get_entity_annotations(entity_id=id)

@mcp.custom_route("/resources/datasets/{id}/children", methods=["GET"])
async def resource_get_dataset_children(id: str, user: dict = Depends(require_mcp_auth)):
    """Get dataset children."""
    return get_entity_children(entity_id=id)

@mcp.custom_route("/resources/datasets/{id}/parent", methods=["GET"])
async def resource_get_dataset_parent(id: str, user: dict = Depends(require_mcp_auth)):
    """Get dataset parent."""
    from synapse_mcp import get_dataset_parent
    return get_dataset_parent(id)

# Folder resources
@mcp.custom_route("/resources/folders/{id_or_name}", methods=["GET"])
async def resource_get_folder(id_or_name: str, user: dict = Depends(require_mcp_auth)):
    """Get folder by ID or name."""
    from synapse_mcp import get_folder_by_id_or_name
    return get_folder_by_id_or_name(id_or_name)

@mcp.custom_route("/resources/folders/{id}/annotations", methods=["GET"])
async def resource_get_folder_annotations(id: str, user: dict = Depends(require_mcp_auth)):
    """Get folder annotations."""
    return get_entity_annotations(entity_id=id)

@mcp.custom_route("/resources/folders/{id}/children", methods=["GET"])
async def resource_get_folder_children(id: str, user: dict = Depends(require_mcp_auth)):
    """Get folder children."""
    return get_entity_children(entity_id=id)

@mcp.custom_route("/resources/folders/{id}/parent", methods=["GET"])
async def resource_get_folder_parent(id: str, user: dict = Depends(require_mcp_auth)):
    """Get folder parent."""
    from synapse_mcp import get_folder_parent
    return get_folder_parent(id)

# File resources
@mcp.custom_route("/resources/files/{id_or_name}", methods=["GET"])
async def resource_get_file(id_or_name: str, user: dict = Depends(require_mcp_auth)):
    """Get file by ID or name."""
    from synapse_mcp import get_file_by_id_or_name
    return get_file_by_id_or_name(id_or_name)

@mcp.custom_route("/resources/files/{id}/annotations", methods=["GET"])
async def resource_get_file_annotations(id: str, user: dict = Depends(require_mcp_auth)):
    """Get file annotations."""
    return get_entity_annotations(entity_id=id)

@mcp.custom_route("/resources/files/{id}/children", methods=["GET"])
async def resource_get_file_children(id: str, user: dict = Depends(require_mcp_auth)):
    """Get file children."""
    from synapse_mcp import get_file_children
    return get_file_children(id)

@mcp.custom_route("/resources/files/{id}/parent", methods=["GET"])
async def resource_get_file_parent(id: str, user: dict = Depends(require_mcp_auth)):
    """Get file parent."""
    from synapse_mcp import get_file_parent
    return get_file_parent(id)

# Table resources
@mcp.custom_route("/resources/tables/{id_or_name}", methods=["GET"])
async def resource_get_table(id_or_name: str, user: dict = Depends(require_mcp_auth)):
    """Get table by ID or name."""
    from synapse_mcp import get_table_by_id_or_name
    return get_table_by_id_or_name(id_or_name)

@mcp.custom_route("/resources/tables/{id}/annotations", methods=["GET"])
async def resource_get_table_annotations(id: str, user: dict = Depends(require_mcp_auth)):
    """Get table annotations."""
    return get_entity_annotations(entity_id=id)

@mcp.custom_route("/resources/tables/{id}/children", methods=["GET"])
async def resource_get_table_children(id: str, user: dict = Depends(require_mcp_auth)):
    """Get table children."""
    from synapse_mcp import get_table_children
    return get_table_children(id)

@mcp.custom_route("/resources/tables/{id}/parent", methods=["GET"])
async def resource_get_table_parent(id: str, user: dict = Depends(require_mcp_auth)):
    """Get table parent."""    
    from synapse_mcp import get_table_parent
    return get_table_parent(id)
