import synapseclient
from typing import Dict, List, Any, Optional, Union, cast

class QueryBuilder:
    """Builder for Synapse queries."""
    
    def __init__(self, synapse_client: synapseclient.Synapse):
        """Initialize with a Synapse client."""
        self.synapse_client = synapse_client
    
    def build_id_query(self, entity_id: str) -> str:
        """Build a query to find an entity by ID.
        
        Args:
            entity_id: The Synapse ID of the entity
            
        Returns:
            Query string
        """
        return f"id == '{entity_id}'"
    
    def build_parent_id_query(self, parent_id: str) -> str:
        """Build a query to find entities by parent ID.
        
        Args:
            parent_id: The Synapse ID of the parent entity
            
        Returns:
            Query string
        """
        return f"parentId == '{parent_id}'"
    
    def build_name_query(self, name: str) -> str:
        """Build a query to find entities by name.
        
        Args:
            name: The name of the entity
            
        Returns:
            Query string
        """
        return f"name == '{name}'"
    
    def build_annotation_query(self, annotations: Dict[str, Any]) -> str:
        """Build a query to find entities by annotations.
        
        Args:
            annotations: Dictionary of annotation key-value pairs
            
        Returns:
            Query string
        """
        query_parts = []
        for key, value in annotations.items():
            if isinstance(value, str):
                query_parts.append(f"{key} == '{value}'")
            elif isinstance(value, (int, float, bool)):
                query_parts.append(f"{key} == {value}")
            elif isinstance(value, list):
                # Handle list values
                if all(isinstance(v, str) for v in value):
                    values_str = ", ".join(f"'{v}'" for v in value)
                else:
                    values_str = ", ".join(str(v) for v in value)
                query_parts.append(f"{key} in ({values_str})")
        
        return " AND ".join(query_parts)
    
    def build_combined_query(self, params: Dict[str, Any]) -> str:
        """Build a combined query from multiple parameters.
        
        Args:
            params: Dictionary of query parameters
            
        Returns:
            Combined query string
        """
        query_parts = []
        
        # Add entity ID if provided
        if 'id' in params:
            query_parts.append(self.build_id_query(params['id']))
        
        # Add parent ID if provided
        if 'parent_id' in params:
            query_parts.append(self.build_parent_id_query(params['parent_id']))
        
        # Add name if provided
        if 'name' in params:
            query_parts.append(self.build_name_query(params['name']))
        
        # Add entity type if provided
        if 'entity_type' in params:
            entity_type = params['entity_type']
            if entity_type.lower() == 'project':
                query_parts.append("nodeType == 'project'")
            elif entity_type.lower() == 'folder':
                query_parts.append("nodeType == 'folder'")
            elif entity_type.lower() == 'file':
                query_parts.append("nodeType == 'file'")
            elif entity_type.lower() == 'table':
                query_parts.append("nodeType == 'table'")
            elif entity_type.lower() == 'dataset':
                query_parts.append("nodeType == 'dataset'")
        
        # Add annotations if provided
        if 'annotations' in params and isinstance(params['annotations'], dict):
            query_parts.append(self.build_annotation_query(params['annotations']))
        
        # Combine all query parts with AND
        return " AND ".join(query_parts)
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a query and return the results.
        
        Args:
            query: Query string
            
        Returns:
            List of entities matching the query
        """
        try:
            # Execute the query using the Synapse client
            results = self.synapse_client.restGET(f"/entity/query?query={query}")
            
            # Format the results
            if isinstance(results, dict) and 'results' in results:
                result_list = results.get('results', [])
                if isinstance(result_list, list):
                    return result_list
            
            return []
        except Exception as e:
            # Return error information
            return [{'error': str(e), 'query': query}]