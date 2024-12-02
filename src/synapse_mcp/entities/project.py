import synapseclient
from typing import Dict, List, Any, Optional

from .base import BaseEntityOperations

class ProjectOperations(BaseEntityOperations):
    """Operations for Synapse Project entities."""
    
    def get_project_children(self, project_id: str) -> List[Dict[str, Any]]:
        """Get children of a project.
        
        Args:
            project_id: The Synapse ID of the project
            
        Returns:
            List of child entities
        """
        children = self.synapse_client.getChildren(project_id)
        return [self.format_entity(child) for child in children]