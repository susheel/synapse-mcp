#!/usr/bin/env python3
"""
Script to run the Synapse MCP server.
"""

import argparse
import logging
import sys
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

# Import the MCP server
from synapse_mcp import mcp, authenticate, get_oauth_url, get_entity, get_entity_annotations, get_entity_children, search_entities, get_datasets_as_croissant
from synapse_mcp import query_entities, query_table

# Create a FastAPI app
app = FastAPI(title="Synapse MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server info endpoint
@app.get("/info")
async def get_info():
    """Get server info."""
    return {
        "name": "Synapse MCP Server",
        "url": os.environ.get("MCP_SERVER_URL", f"mcp://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('PORT', '9000')}"),
        "oauth_enabled": True,
        "version": "0.1.0"
    }

# List tools endpoint
@app.get("/tools")
async def list_tools():
    """List available tools."""
    return [
        {
            "name": "authenticate",
            "description": "Authenticate with Synapse using Auth Token or OAuth2"
        },
        {
            "name": "get_oauth_url",
            "description": "Get the OAuth2 authorization URL for Synapse"
            
        },
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

# List resources endpoint
@app.get("/resources")
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

# Tool endpoints
@app.post("/tools/authenticate")
async def tool_authenticate(request: Request):
    """Authenticate with Synapse."""
    data = await request.json()
    return authenticate(**data)

@app.post("/tools/get_oauth_url")
async def tool_get_oauth_url(request: Request):
    """Get the OAuth2 authorization URL for Synapse."""
    data = await request.json()
    return get_oauth_url(**data)

# OAuth2 endpoints
@app.get("/oauth/login")
async def oauth_login(client_id: str, redirect_uri: str, scope: str = "view"):
    """Redirect to Synapse OAuth2 login page."""
    result = get_oauth_url(client_id=client_id, redirect_uri=redirect_uri, scope=scope)
    if result.get("success", False):
        return RedirectResponse(url=result["auth_url"])
    return {"error": result.get("message", "Failed to generate OAuth URL")}

@app.get("/oauth/callback")
async def oauth_callback(code: str, state: str = "", client_id: str = "", redirect_uri: str = ""):
    """Handle OAuth2 callback from Synapse."""
    # If client_id and redirect_uri are not provided in the query params,
    # try to get them from environment variables
    client_id = client_id or os.environ.get("SYNAPSE_OAUTH_CLIENT_ID", "")
    redirect_uri = redirect_uri or os.environ.get("SYNAPSE_OAUTH_REDIRECT_URI", "")
    client_secret = os.environ.get("SYNAPSE_OAUTH_CLIENT_SECRET", "")
    
    if not client_id or not redirect_uri or not client_secret:
        return {"error": "Missing OAuth2 configuration. Please provide client_id, redirect_uri, and ensure client_secret is set in environment variables."}
    
    # Authenticate with the code
    result = authenticate(
        oauth_code=code, 
        redirect_uri=redirect_uri,
        client_id=client_id,
        client_secret=client_secret
    )
    return result

@app.post("/tools/get_entity")
async def tool_get_entity(request: Request):
    """Get an entity by ID."""
    data = await request.json()
    return get_entity(**data)

@app.post("/tools/get_entity_annotations")
async def tool_get_entity_annotations(request: Request):
    """Get annotations for an entity."""
    data = await request.json()
    return get_entity_annotations(**data)

@app.post("/tools/get_entity_children")
async def tool_get_entity_children(request: Request):
    """Get child entities of a container entity."""
    data = await request.json()
    return get_entity_children(**data)

@app.post("/tools/search_entities")
async def tool_search_entities(request: Request):
    """Search for Synapse entities."""
    data = await request.json()
    return search_entities(**data)


@app.post("/tools/query_entities")
async def tool_query_entities(request: Request):
    """Query entities based on various criteria."""
    data = await request.json()
    return query_entities(**data)

@app.post("/tools/query_table")
async def tool_query_table(request: Request):
    """Query a Synapse table."""
    data = await request.json()
    return query_table(**data)

@app.post("/tools/get_datasets_as_croissant")
async def tool_get_datasets_as_croissant(request: Request):
    """Get public datasets in Croissant metadata format."""
    data = await request.json()
    return get_datasets_as_croissant(**data)

# Resource endpoints
@app.get("/resources/entities/{id_or_name}")
async def resource_get_entity(id_or_name: str):
    """Get entity by ID or name."""
    from synapse_mcp import get_entity_by_id_or_name
    return get_entity_by_id_or_name(id_or_name)

@app.get("/resources/entities/{id}/annotations")
async def resource_get_entity_annotations(id: str):
    """Get entity annotations."""
    return get_entity_annotations(entity_id=id)

@app.get("/resources/entities/{id}/children")
async def resource_get_entity_children(id: str):
    """Get entity children."""
    return get_entity_children(entity_id=id)

@app.get("/resources/entities/{entity_type}")
async def resource_query_entities_by_type(entity_type: str):
    """Query entities by type."""
    return query_entities(entity_type=entity_type)

@app.get("/resources/entities/parent/{parent_id}")
async def resource_query_entities_by_parent(parent_id: str):
    """Query entities by parent ID."""
    return query_entities(parent_id=parent_id)

# Project resources
@app.get("/resources/projects/{id_or_name}")
async def resource_get_project(id_or_name: str):
    """Get project by ID or name."""
    from synapse_mcp import get_project_by_id_or_name
    return get_project_by_id_or_name(id_or_name)

@app.get("/resources/projects/{id}/annotations")
async def resource_get_project_annotations(id: str):
    """Get project annotations."""
    return get_entity_annotations(entity_id=id)

@app.get("/resources/projects/{id}/children")
async def resource_get_project_children(id: str):
    """Get project children."""
    return get_entity_children(entity_id=id)

@app.get("/resources/projects/{id}/parent")
async def resource_get_project_parent(id: str):
    """Get project parent."""
    from synapse_mcp import get_project_parent
    return get_project_parent(id)

# Dataset resources
@app.get("/resources/datasets/{id_or_name}")
async def resource_get_dataset(id_or_name: str):
    """Get dataset by ID or name."""
    from synapse_mcp import get_dataset_by_id_or_name
    return get_dataset_by_id_or_name(id_or_name)

@app.get("/resources/datasets/{id}/annotations")
async def resource_get_dataset_annotations(id: str):
    """Get dataset annotations."""
    return get_entity_annotations(entity_id=id)

@app.get("/resources/datasets/{id}/children")
async def resource_get_dataset_children(id: str):
    """Get dataset children."""
    return get_entity_children(entity_id=id)

@app.get("/resources/datasets/{id}/parent")
async def resource_get_dataset_parent(id: str):
    """Get dataset parent."""
    from synapse_mcp import get_dataset_parent
    return get_dataset_parent(id)

# Folder resources
@app.get("/resources/folders/{id_or_name}")
async def resource_get_folder(id_or_name: str):
    """Get folder by ID or name."""
    from synapse_mcp import get_folder_by_id_or_name
    return get_folder_by_id_or_name(id_or_name)

@app.get("/resources/folders/{id}/annotations")
async def resource_get_folder_annotations(id: str):
    """Get folder annotations."""
    return get_entity_annotations(entity_id=id)

@app.get("/resources/folders/{id}/children")
async def resource_get_folder_children(id: str):
    """Get folder children."""
    return get_entity_children(entity_id=id)

@app.get("/resources/folders/{id}/parent")
async def resource_get_folder_parent(id: str):
    """Get folder parent."""
    from synapse_mcp import get_folder_parent
    return get_folder_parent(id)

# File resources
@app.get("/resources/files/{id_or_name}")
async def resource_get_file(id_or_name: str):
    """Get file by ID or name."""
    from synapse_mcp import get_file_by_id_or_name
    return get_file_by_id_or_name(id_or_name)

@app.get("/resources/files/{id}/annotations")
async def resource_get_file_annotations(id: str):
    """Get file annotations."""
    return get_entity_annotations(entity_id=id)

@app.get("/resources/files/{id}/children")
async def resource_get_file_children(id: str):
    """Get file children."""
    from synapse_mcp import get_file_children
    return get_file_children(id)

@app.get("/resources/files/{id}/parent")
async def resource_get_file_parent(id: str):
    """Get file parent."""
    from synapse_mcp import get_file_parent
    return get_file_parent(id)

# Table resources
@app.get("/resources/tables/{id_or_name}")
async def resource_get_table(id_or_name: str):
    """Get table by ID or name."""
    from synapse_mcp import get_table_by_id_or_name
    return get_table_by_id_or_name(id_or_name)

@app.get("/resources/tables/{id}/annotations")
async def resource_get_table_annotations(id: str):
    """Get table annotations."""
    return get_entity_annotations(entity_id=id)

@app.get("/resources/tables/{id}/children")
async def resource_get_table_children(id: str):
    """Get table children."""
    from synapse_mcp import get_table_children
    return get_table_children(id)

@app.get("/resources/tables/{id}/parent")
async def resource_get_table_parent(id: str):
    """Get table parent."""
    from synapse_mcp import get_table_parent
    return get_table_parent(id)

@app.get("/resources/query/table/{id}/{query}")
async def resource_query_table(id: str, query: str):
    """Query a table with SQL-like syntax."""
    return query_table(table_id=id, query=query)

@app.get("/resources/croissant/datasets")
async def resource_get_datasets_as_croissant():
    """Get public datasets in Croissant metadata format."""
    return get_datasets_as_croissant()
    
def main():
    """Run the Synapse MCP server."""
    parser = argparse.ArgumentParser(description="Run the Synapse MCP server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--server-url", help="Public URL of the server (for OAuth2 redirect)")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Set server URL for OAuth2
    server_url = None
    if args.server_url:
        server_url = args.server_url
    elif "MCP_SERVER_URL" in os.environ:
        server_url = os.environ["MCP_SERVER_URL"]
    else:
        # Default server URL based on host and port
        server_url = f"mcp://{args.host}:{args.port}"
        os.environ["MCP_SERVER_URL"] = server_url
    
    # Log server information
    logger = logging.getLogger("synapse_mcp")
    logger.info(f"Starting Synapse MCP server on {args.host}:{args.port}")
    
    # Run the server using uvicorn
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()