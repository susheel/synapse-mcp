import synapseclient
from typing import Dict, List, Any, Optional, Union

class BaseEntityOperations:
    """Base class for entity operations."""
    
    def __init__(self, synapse_client: synapseclient.Synapse):
        """Initialize with a Synapse client."""
        self.synapse_client = synapse_client
    
    def get_entity_by_id(self, entity_id: str) -> Dict[str, Any]:
        """Get an entity by ID.
        
        Args:
            entity_id: The Synapse ID of the entity
            
        Returns:
            The entity as a dictionary
        """
        entity = self.synapse_client.get(entity_id)
        return self.format_entity(entity)
    
    def get_entity_annotations(self, entity_id: str) -> Dict[str, Any]:
        """Get annotations for an entity.
        
        Args:
            entity_id: The Synapse ID of the entity
            
        Returns:
            The entity annotations as a dictionary
        """
        # Get annotations using the get_annotations method
        annotations = self.synapse_client.get_annotations(entity_id)
            
        # Ensure we return a dictionary
        if annotations is None:
            return {}
        return annotations
    
    def format_entity(self, entity: Any) -> Dict[str, Any]:
        """Format a Synapse entity as a dictionary.
        
        Args:
            entity: The Synapse entity
            
        Returns:
            The entity as a dictionary
        """
        # If entity is already a dictionary, return it
        if isinstance(entity, dict):
            return entity
            
        # Convert entity to a dictionary
        if hasattr(entity, 'to_dict'):
            entity_dict = entity.to_dict()
        else:
            # If entity doesn't have to_dict method, convert it manually
            entity_dict = {
                'id': entity.id if hasattr(entity, 'id') else None,
                'name': entity.name if hasattr(entity, 'name') else None,
                'type': entity.concreteType.split('.')[-1] if hasattr(entity, 'concreteType') else None,
                'parentId': entity.parentId if hasattr(entity, 'parentId') else None,
                'createdOn': entity.createdOn if hasattr(entity, 'createdOn') else None,
                'modifiedOn': entity.modifiedOn if hasattr(entity, 'modifiedOn') else None,
                'createdBy': entity.createdBy if hasattr(entity, 'createdBy') else None,
                'modifiedBy': entity.modifiedBy if hasattr(entity, 'modifiedBy') else None,
            }
        
        return entity_dict
    
    def query_entities(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query entities based on parameters.
        
        Args:
            query_params: Query parameters
            
        Returns:
            List of entities matching the query
        """
        # This will be implemented in the query module
        # For now, return an empty list
        return []