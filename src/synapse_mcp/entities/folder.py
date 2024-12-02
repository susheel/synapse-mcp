import synapseclient
from typing import Dict, List, Any, Optional

from .base import BaseEntityOperations

class FolderOperations(BaseEntityOperations):
    """Operations for Synapse Folder entities."""
    
    def get_folder_children(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get children of a folder.
        
        Args:
            folder_id: The Synapse ID of the folder
            
        Returns:
            List of child entities
        """
        children = self.synapse_client.getChildren(folder_id)
        return [self.format_entity(child) for child in children]