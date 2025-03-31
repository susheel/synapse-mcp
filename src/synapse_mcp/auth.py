import synapseclient
import requests
import json
import os
from typing import Optional, Any, Dict
from urllib.parse import urlencode

class SynapseAuth:
    def __init__(self):
        self.synapse_client: Optional[synapseclient.Synapse] = None
        
    def authenticate(self, auth_token: Optional[str] = None) -> None:
        """Authenticate with Synapse using Auth Token."""
        # Create a new Synapse client instance and authenticate with token
        self.synapse_client = synapseclient.Synapse()
        
        try:
            if auth_token:
                self.synapse_client.login(authToken=auth_token)
            else:
                raise ValueError("Auth token must be provided")
        except ValueError as e:
            self.synapse_client = None
            raise
        except Exception as e:
            self.synapse_client = None
            raise RuntimeError(f"Authentication failed: {str(e)}")
            
    def authenticate_with_oauth(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Authenticate with Synapse using OAuth2.
        
        Args:
            code: Authorization code from OAuth2 flow
            redirect_uri: Redirect URI used in the authorization request
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            
        Returns:
            Authentication result with access token
        """
        try:
            # Exchange authorization code for access token
            token_url = "https://repo-prod.prod.sagebase.org/auth/v1/oauth2/token"
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()
            
            # Authenticate with the access token
            self.authenticate(auth_token=token_info.get("access_token"))
            
            return {
                "success": True,
                "token_info": token_info,
                "message": "Successfully authenticated with Synapse via OAuth2"
            }
        except Exception as e:
            self.synapse_client = None
            return {
                "success": False,
                "message": f"OAuth2 authentication failed: {str(e)}"
            }
    
    def get_oauth_url(self, client_id: str, redirect_uri: str, scope: str = "view") -> str:
        """Get the OAuth2 authorization URL for Synapse.
        
        Returns the URL to redirect the user to for OAuth2 authorization.
        """
        auth_url = f"https://repo-prod.prod.sagebase.org/auth/v1/oauth2/authorize?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code', 'scope': scope})}"
        return auth_url
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