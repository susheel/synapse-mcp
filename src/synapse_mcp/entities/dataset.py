import synapseclient
from typing import Dict, List, Any, Optional

from .base import BaseEntityOperations

class DatasetOperations(BaseEntityOperations):
    """Operations for Synapse Dataset entities."""
    
    def get_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get items in a dataset.
        
        Args:
            dataset_id: The Synapse ID of the dataset
            
        Returns:
            List of dataset items
        """
        try:
            # Get the dataset entity
            dataset = self.synapse_client.get(dataset_id)
            
            # Check if it's a dataset
            if not hasattr(dataset, 'items') and not hasattr(dataset, 'datasetItems'):
                raise ValueError(f"Entity {dataset_id} is not a dataset")
            
            # Get dataset items
            items = getattr(dataset, 'items', None) or getattr(dataset, 'datasetItems', [])
            
            # Format each item
            formatted_items = []
            for item in items:
                formatted_item = {
                    'id': item.get('id') if hasattr(item, 'get') else getattr(item, 'id', None),
                    'name': item.get('name') if hasattr(item, 'get') else getattr(item, 'name', None),
                    'type': item.get('type') if hasattr(item, 'get') else getattr(item, 'type', None),
                    'entityId': item.get('entityId') if hasattr(item, 'get') else getattr(item, 'entityId', None),
                    'versionNumber': item.get('versionNumber') if hasattr(item, 'get') else getattr(item, 'versionNumber', None),
                }
                formatted_items.append(formatted_item)
                
            return formatted_items
        except Exception as e:
            # Return error information
            return [{'error': str(e), 'dataset_id': dataset_id}]