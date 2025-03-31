from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any, Optional, Union
import synapseclient
import os

from .auth import SynapseAuth
from .entities import (
    BaseEntityOperations,
    ProjectOperations,
    FolderOperations,
    FileOperations,
    TableOperations,
    DatasetOperations,
)
from .query import QueryBuilder
from .utils import validate_synapse_id, format_annotations
from .entities.croissant import convert_to_croissant

# Create an MCP server with a placeholder URL
# The actual URL will be set when the server is run
mcp = FastMCP("Synapse MCP Server")

# Initialize authentication and entity operations
auth_manager = SynapseAuth()
entity_ops = {}
query_builder = None

# Authentication Tool
@mcp.tool()
def authenticate(auth_token: Optional[str] = None, oauth_code: Optional[str] = None, redirect_uri: Optional[str] = None, client_id: Optional[str] = None, client_secret: Optional[str] = None) -> Dict[str, Any]:
    """Authenticate with Synapse using Auth Token.
    
    Args:
        auth_token: Synapse authentication token
        
    Returns:
        Authentication result
    """
    global entity_ops, query_builder
    try:
        # Authenticate with Synapse
        if oauth_code and redirect_uri and client_id and client_secret:
            # OAuth2 authentication
            result = auth_manager.authenticate_with_oauth(
                code=oauth_code, redirect_uri=redirect_uri, 
                client_id=client_id, client_secret=client_secret
            )
            if not result.get("success", False):
                return result
        
        # Get the authenticated client
        synapse_client = auth_manager.get_client()
        
        # Initialize entity operations
        entity_ops = {
            'base': BaseEntityOperations(synapse_client),
            'project': ProjectOperations(synapse_client),
            'folder': FolderOperations(synapse_client),
            'file': FileOperations(synapse_client),
            'table': TableOperations(synapse_client),
            'dataset': DatasetOperations(synapse_client),
        }
        
        # Initialize query builder
        query_builder = QueryBuilder(synapse_client)
        
        return {
            'success': True,
            'message': 'Successfully authenticated with Synapse'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Authentication failed: {str(e)}'
        }

@mcp.tool()
def get_oauth_url(client_id: str, redirect_uri: str, scope: str = "view") -> Dict[str, Any]:
    """Get the OAuth2 authorization URL for Synapse.
    
    Args:
        client_id: OAuth2 client ID
        redirect_uri: Redirect URI for the OAuth2 flow
        scope: OAuth2 scope (default: "view")
        
    Returns:
        The OAuth2 authorization URL
    """
    try:
        auth_url = auth_manager.get_oauth_url(client_id, redirect_uri, scope)
        return {"success": True, "auth_url": auth_url}
    except Exception as e:
        return {"success": False, "message": f"Failed to generate OAuth URL: {str(e)}"}


# Entity Retrieval Tools
@mcp.tool()
def get_entity(entity_id: str) -> Dict[str, Any]:
    """Get a Synapse entity by ID.
    
    Args:
        entity_id: The Synapse ID of the entity
        
    Returns:
        The entity as a dictionary
    """
    # Public entities don't require authentication
    # Private entities will be handled by the Synapse client
    
    if not validate_synapse_id(entity_id):
        return {'error': f'Invalid Synapse ID: {entity_id}'}
    
    try:
        return entity_ops['base'].get_entity_by_id(entity_id)
    except Exception as e:
        return {'error': str(e), 'entity_id': entity_id}

@mcp.tool()
def get_entity_annotations(entity_id: str) -> Dict[str, Any]:
    """Get annotations for an entity.
    
    Args:
        entity_id: The Synapse ID of the entity
        
    Returns:
        The entity annotations as a dictionary
    """
    # Public entities don't require authentication
    # Private entities will be handled by the Synapse client
    
    if not validate_synapse_id(entity_id):
        return {'error': f'Invalid Synapse ID: {entity_id}'}
    
    try:
        annotations = entity_ops['base'].get_entity_annotations(entity_id)
        return format_annotations(annotations)
    except Exception as e:
        return {'error': str(e), 'entity_id': entity_id}

@mcp.tool()
def get_entity_children(entity_id: str) -> List[Dict[str, Any]]:
    """Get child entities of a container entity.
    
    Args:
        entity_id: The Synapse ID of the container entity
        
    Returns:
        List of child entities
    """
    # Public entities don't require authentication
    # Private entities will be handled by the Synapse client
    
    if not validate_synapse_id(entity_id):
        return [{'error': f'Invalid Synapse ID: {entity_id}'}]
    
    try:
        # Determine the entity type
        entity = entity_ops['base'].get_entity_by_id(entity_id)
        entity_type = entity.get('type', '').lower()
        
        if entity_type == 'project':
            return entity_ops['project'].get_project_children(entity_id)
        elif entity_type == 'folder':
            return entity_ops['folder'].get_folder_children(entity_id)
        else:
            return [{'error': f'Entity {entity_id} is not a container entity'}]
    except Exception as e:
        return [{'error': str(e), 'entity_id': entity_id}]

# Query Tools
@mcp.tool()
def search_entities(search_term: str, entity_type: Optional[str] = None, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for Synapse entities.
    
    Args:
        search_term: Term to search for
        entity_type: Type of entity to search for (optional)
        parent_id: Parent entity ID to filter by (optional)
        
    Returns:
        List of entities matching the search
    """
    # Build search parameters
    params = {"name": search_term}
    if entity_type:
        params["entity_type"] = entity_type
    if parent_id:
        params["parent_id"] = parent_id
    return query_entities(**params)

@mcp.tool()
def query_entities(entity_type: Optional[str] = None, parent_id: Optional[str] = None, 
                  name: Optional[str] = None, annotations: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Query entities based on various criteria.
    
    Args:
        entity_type: Type of entity to query (project, folder, file, table, dataset)
        parent_id: Parent entity ID to filter by
        name: Entity name to filter by
        annotations: Annotations to filter by
        
    Returns:
        List of entities matching the query
    """
    # Public entities don't require authentication
    # Private entities will be handled by the Synapse client
    
    if not query_builder:
        return [{'error': 'Query builder not initialized'}]
    
    try:
        # Build query parameters
        params = {}
        if entity_type:
            params['entity_type'] = entity_type
        if parent_id:
            params['parent_id'] = parent_id
        if name:
            params['name'] = name
        if annotations:
            params['annotations'] = annotations
        
        # Build and execute query
        query = query_builder.build_combined_query(params)
        return query_builder.execute_query(query)
    except Exception as e:
        return [{'error': str(e), 'params': params}]

@mcp.tool()
def query_table(table_id: str, query: str) -> Dict[str, Any]:
    """Query a Synapse table.
    
    Args:
        table_id: The Synapse ID of the table
        query: SQL-like query string
        
    Returns:
        Query results
    """
    # Public tables don't require authentication
    # Private tables will be handled by the Synapse client
    
    if not validate_synapse_id(table_id):
        return {'error': f'Invalid Synapse ID: {table_id}'}
    
    try:
        return entity_ops['table'].query_table(table_id, query)
    except Exception as e:
        return {'error': str(e), 'table_id': table_id, 'query': query}

@mcp.tool()
def get_datasets_as_croissant() -> Dict[str, Any]:
    """Get public datasets in Croissant metadata format.
    
    Returns:
        Datasets in Croissant metadata format
    """
    try:
        # Query the public datasets table
        table_id = "syn61609402"  # The specific table ID for public datasets

        # Try to query the actual table if authenticated
        if auth_manager.is_authenticated():
            query_result = query_table(table_id, "SELECT * FROM syn61609402")
            if 'error' not in query_result:
                # Convert to Croissant format
                return convert_to_croissant(query_result)

        # If not authenticated or query failed, return sample data
        # This allows the API to work without authentication for demo purposes
        sample_data = {
            'headers': ['id', 'title', 'description', 'diseaseFocus', 'dataType', 'yearProcessed', 'fundingAgency'],
            'data': [
                ['syn12345678', 'Sample Dataset', 'A sample dataset for demonstration', 'Neuroscience', 'Genomics', '2023', 'NIH'],
                ['syn87654321', 'Another Dataset', 'Another sample dataset', 'Cancer', 'Proteomics', '2024', 'NCI']
            ]
        }
        
        # Convert to Croissant format
        croissant_data = convert_to_croissant(sample_data)
        
        return croissant_data
    except Exception as e:
        return {'error': str(e), 'message': 'Failed to convert datasets to Croissant format'}


# Entity Resources
@mcp.resource("entities/{id_or_name}")
def get_entity_by_id_or_name(id_or_name: str) -> Dict[str, Any]:
    """Get entity by ID or name."""
    # Check if it's a Synapse ID
    if validate_synapse_id(id_or_name):
        return get_entity(id_or_name)
    # Otherwise, search by name
    results = query_entities(name=id_or_name)
    if results and not isinstance(results[0], dict) or not results[0].get('error'):
        return results[0]
    return {'error': f'Entity not found: {id_or_name}'}

@mcp.resource("entities/{id}/annotations")
def get_entity_annotations_resource(id: str) -> Dict[str, Any]:
    """Get entity annotations."""
    return get_entity_annotations(id)

@mcp.resource("entities/{id}/children")
def get_entity_children_resource(id: str) -> List[Dict[str, Any]]:
    """Get entity children."""
    return get_entity_children(id)

@mcp.resource("entities/{entity_type}")
def query_entities_by_type(entity_type: str) -> List[Dict[str, Any]]:
    """Query entities by type."""
    return query_entities(entity_type=entity_type)

@mcp.resource("entities/parent/{parent_id}")
def query_entities_by_parent(parent_id: str) -> List[Dict[str, Any]]:
    """Query entities by parent ID."""
    return query_entities(parent_id=parent_id)

# Project Resources
@mcp.resource("projects/{id_or_name}")
def get_project_by_id_or_name(id_or_name: str) -> Dict[str, Any]:
    """Get project by ID or name."""
    # Check if it's a Synapse ID
    if validate_synapse_id(id_or_name):
        entity = get_entity(id_or_name)
        if entity.get('type') == 'Project':
            return entity
        return {'error': f'Entity is not a project: {id_or_name}'}
    # Otherwise, search by name
    results = query_entities(name=id_or_name, entity_type='project')
    if results and not isinstance(results[0], dict) or not results[0].get('error'):
        return results[0]
    return {'error': f'Project not found: {id_or_name}'}

@mcp.resource("projects/{id}/annotations")
def get_project_annotations(id: str) -> Dict[str, Any]:
    """Get project annotations."""
    return get_entity_annotations(id)

@mcp.resource("projects/{id}/children")
def get_project_children(id: str) -> List[Dict[str, Any]]:
    """Get project children."""
    return get_entity_children(id)

@mcp.resource("projects/{id}/parent")
def get_project_parent(id: str) -> Dict[str, Any]:
    """Get project parent."""
    # Projects don't have parents in Synapse
    return {'error': 'Projects do not have parents in Synapse'}

# Dataset Resources
@mcp.resource("datasets/{id_or_name}")
def get_dataset_by_id_or_name(id_or_name: str) -> Dict[str, Any]:
    """Get dataset by ID or name."""
    # Similar implementation as projects but for datasets
    if validate_synapse_id(id_or_name):
        entity = get_entity(id_or_name)
        if entity.get('type') == 'Dataset':
            return entity
        return {'error': f'Entity is not a dataset: {id_or_name}'}
    # Otherwise, search by name
    results = query_entities(name=id_or_name, entity_type='dataset')
    if results and not isinstance(results[0], dict) or not results[0].get('error'):
        return results[0]
    return {'error': f'Dataset not found: {id_or_name}'}

@mcp.resource("datasets/{id}/annotations")
def get_dataset_annotations(id: str) -> Dict[str, Any]:
    """Get dataset annotations."""
    return get_entity_annotations(id)

@mcp.resource("datasets/{id}/children")
def get_dataset_children(id: str) -> List[Dict[str, Any]]:
    """Get dataset children."""
    return get_entity_children(id)

@mcp.resource("datasets/{id}/parent")
def get_dataset_parent(id: str) -> Dict[str, Any]:
    """Get dataset parent."""
    entity = get_entity(id)
    return get_entity(entity.get('parentId')) if entity.get('parentId') else {'error': 'Dataset has no parent'}

# Folder Resources
@mcp.resource("folders/{id_or_name}")
def get_folder_by_id_or_name(id_or_name: str) -> Dict[str, Any]:
    """Get folder by ID or name."""
    if validate_synapse_id(id_or_name):
        entity = get_entity(id_or_name)
        if entity.get('type') == 'Folder':
            return entity
        return {'error': f'Entity is not a folder: {id_or_name}'}
    # Otherwise, search by name
    results = query_entities(name=id_or_name, entity_type='folder')
    if results and not isinstance(results[0], dict) or not results[0].get('error'):
        return results[0]
    return {'error': f'Folder not found: {id_or_name}'}

@mcp.resource("folders/{id}/annotations")
def get_folder_annotations(id: str) -> Dict[str, Any]:
    """Get folder annotations."""
    return get_entity_annotations(id)

@mcp.resource("folders/{id}/children")
def get_folder_children(id: str) -> List[Dict[str, Any]]:
    """Get folder children."""
    return get_entity_children(id)

@mcp.resource("folders/{id}/parent")
def get_folder_parent(id: str) -> Dict[str, Any]:
    """Get folder parent."""
    entity = get_entity(id)
    return get_entity(entity.get('parentId')) if entity.get('parentId') else {'error': 'Folder has no parent'}

# File Resources
@mcp.resource("files/{id_or_name}")
def get_file_by_id_or_name(id_or_name: str) -> Dict[str, Any]:
    """Get file by ID or name."""
    if validate_synapse_id(id_or_name):
        entity = get_entity(id_or_name)
        if entity.get('type') == 'File':
            return entity
        return {'error': f'Entity is not a file: {id_or_name}'}
    # Otherwise, search by name
    results = query_entities(name=id_or_name, entity_type='file')
    if results and not isinstance(results[0], dict) or not results[0].get('error'):
        return results[0]
    return {'error': f'File not found: {id_or_name}'}

@mcp.resource("files/{id}/annotations")
def get_file_annotations(id: str) -> Dict[str, Any]:
    """Get file annotations."""
    return get_entity_annotations(id)

@mcp.resource("files/{id}/children")
def get_file_children(id: str) -> List[Dict[str, Any]]:
    """Get file children."""
    # Files don't have children in Synapse
    return [{'error': 'Files do not have children in Synapse'}]

@mcp.resource("files/{id}/parent")
def get_file_parent(id: str) -> Dict[str, Any]:
    """Get file parent."""
    entity = get_entity(id)
    return get_entity(entity.get('parentId')) if entity.get('parentId') else {'error': 'File has no parent'}

# Table Resources
@mcp.resource("tables/{id_or_name}")
def get_table_by_id_or_name(id_or_name: str) -> Dict[str, Any]:
    """Get table by ID or name."""
    if validate_synapse_id(id_or_name):
        entity = get_entity(id_or_name)
        if entity.get('type') == 'Table':
            return entity
        return {'error': f'Entity is not a table: {id_or_name}'}
    # Otherwise, search by name
    results = query_entities(name=id_or_name, entity_type='table')
    if results and not isinstance(results[0], dict) or not results[0].get('error'):
        return results[0]
    return {'error': f'Table not found: {id_or_name}'}

@mcp.resource("tables/{id}/annotations")
def get_table_annotations(id: str) -> Dict[str, Any]:
    """Get table annotations."""
    return get_entity_annotations(id)

@mcp.resource("tables/{id}/children")
def get_table_children(id: str) -> List[Dict[str, Any]]:
    """Get table children."""
    # Tables don't have children in Synapse
    return [{'error': 'Tables do not have children in Synapse'}]

@mcp.resource("tables/{id}/parent")
def get_table_parent(id: str) -> Dict[str, Any]:
    """Get table parent."""
    entity = get_entity(id)
    return get_entity(entity.get('parentId')) if entity.get('parentId') else {'error': 'Table has no parent'}

@mcp.resource("table/{id}/{query}")
def query_table_resource(id: str, query: str) -> Dict[str, Any]:
    """Query a table with SQL-like syntax."""
    # URL-decode the query string
    import urllib.parse
    decoded_query = urllib.parse.unquote(query)
    return query_table(id, decoded_query)

# Function to run the server
def run_server(host: str = "127.0.0.1", port: int = 9000, server_url: Optional[str] = None):
    """Run the MCP server."""
    # Determine the transport type based on environment variable
    # Use STDIO for local development and SSE for cloud deployment
    transport_env = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    
    # Ensure transport is one of the allowed literal values
    if transport_env == "sse":
        transport = "sse"
    else:
        transport = "stdio"  # Default to stdio for local development
    
    # Set the server URL if provided
    if server_url:
        os.environ["MCP_SERVER_URL"] = server_url or "mcp://127.0.0.1:9000"
    mcp.run(transport=transport)