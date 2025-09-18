
import os
import logging
import synapseclient
from urllib.parse import urlencode

class SynapseAuth:
    """
    Manages Synapse authentication for both Personal Access Token (PAT) and OAuth2 flows.
    """
    def __init__(self):
        self.synapse_client: synapseclient.Synapse | None = None
        self.user_profile: dict | None = None

    def authenticate(self, personal_access_token: str) -> None:
        """
        Authenticates with Synapse using a Personal Access Token (PAT).
        """
        logging.info("Attempting to authenticate with Synapse PAT...")
        try:
            client = synapseclient.Synapse()
            client.login(authToken=personal_access_token, silent=True)
            profile = client.getUserProfile()
            self.synapse_client = client
            self.user_profile = profile
            logging.info(f"Successfully authenticated as Synapse user: {profile['userName']} ({profile['ownerId']})")
        except Exception as e:
            logging.error(f"Failed to authenticate with Synapse PAT: {e}")
            self.synapse_client = None
            self.user_profile = None
            raise

    def authenticate_with_oauth(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
        """
        Completes the OAuth2 authentication flow.
        This is a placeholder as the actual implementation would involve exchanging the code for a token.
        """
        # In a real implementation, you would exchange the code for an access token here.
        # For now, we'll just simulate success if a code is provided.
        if code:
            # This is where you would use the synapseclient to complete the OAuth flow.
            # Since the library handles this internally when you call login,
            # this method is more for demonstrating the flow.
            # We'll assume for now that if we get a code, we can get a client.
            self.synapse_client = synapseclient.Synapse()
            # You'd typically login here with the token obtained from the code
            # self.synapse_client.login(authToken=access_token)
            self.user_profile = self.synapse_client.getUserProfile()
            return {"success": True, "message": "OAuth authentication successful (simulated)."}
        return {"success": False, "message": "OAuth authentication failed: No code provided."}


    def get_client(self) -> synapseclient.Synapse | None:
        """
        Returns the authenticated Synapse client.
        """
        return self.synapse_client

    def is_authenticated(self) -> bool:
        """
        Checks if the client is authenticated.
        """
        return self.synapse_client is not None

    def get_oauth_url(self, client_id: str, redirect_uri: str, scope: str = "view", state: str = None) -> str:
        """
        Get the OAuth2 authorization URL for Synapse.
        """
        import uuid
        if state is None:
            state = str(uuid.uuid4())
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': f'openid {scope}',
            'state': state
        }
        auth_url = f"https://signin.synapse.org?{urlencode(params)}"
        return auth_url


