import synapseclient
from typing import Optional, Any

class SynapseAuth:
    def __init__(self):
        self.synapse_client: Optional[synapseclient.Synapse] = None
        
    def authenticate(self, auth_token: Optional[str] = None) -> None:
        """Authenticate with Synapse using Auth Token."""
        # Create a new Synapse client instance
        self.synapse_client = synapseclient.Synapse()
        
        try:
            if auth_token:
                self.synapse_client.login(authToken=auth_token)
            else:
                raise ValueError("Auth token must be provided")
        except Exception as e:
            self.synapse_client = None
            raise RuntimeError(f"Authentication failed: {str(e)}")
        
    def get_client(self) -> synapseclient.Synapse:
        """Get the authenticated Synapse client."""
        if not self.synapse_client:
            raise RuntimeError("Synapse client not initialized")
        try:
            # Test authentication by getting user profile
            self.synapse_client.getUserProfile()
            return self.synapse_client
        except Exception as e:
            raise RuntimeError(f"Not authenticated with Synapse: {str(e)}")
            
    def is_authenticated(self) -> bool:
        """Check if authenticated with Synapse."""
        if not self.synapse_client:
            return False
        try:
            # Test authentication by getting user profile
            self.synapse_client.getUserProfile()
            return True
        except Exception:
            return False