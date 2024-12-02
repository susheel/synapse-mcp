import synapseclient
from typing import Dict, List, Any, Optional

from .base import BaseEntityOperations

class FileOperations(BaseEntityOperations):
    """Operations for Synapse File entities."""
    
    def get_file_content_url(self, file_id: str) -> str:
        """Get the URL for downloading a file's content.
        
        Args:
            file_id: The Synapse ID of the file
            
        Returns:
            URL for downloading the file content
        """
        file_handle = self.synapse_client.get(file_id, downloadFile=False)
        return file_handle.get('_file_handle', {}).get('url', '')
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a file.
        
        Args:
            file_id: The Synapse ID of the file
            
        Returns:
            File metadata as a dictionary
        """
        file_entity = self.synapse_client.get(file_id, downloadFile=False)
        return self.format_entity(file_entity)