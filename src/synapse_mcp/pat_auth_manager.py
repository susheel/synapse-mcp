"""
Manages the server-side authentication state for a Personal Access Token (PAT).
"""
import os
import logging
import synapseclient

# Globals to hold the authenticated client and user profile
logger = logging.getLogger(__name__)

# This is safe for this use case as they are set once at startup.
synapse_client: synapseclient.Synapse | None = None
user_profile: dict | None = None

def initialize_pat_auth():
    """
    Initializes the Synapse client if a PAT is provided in the environment.
    """
    global synapse_client, user_profile
    pat = os.environ.get("SYNAPSE_PAT")
    if pat:
        logger.info("SYNAPSE_PAT environment variable found. Attempting to authenticate...")
        try:
            client = synapseclient.Synapse()
            client.login(authToken=pat, silent=True)
            profile = client.getUserProfile()
            synapse_client = client
            user_profile = profile
            logger.info(f"Successfully authenticated as Synapse user: {profile['userName']} ({profile['ownerId']})")
        except Exception as e:
            logger.error(f"Failed to authenticate with Synapse PAT: {e}")
            synapse_client = None
            user_profile = None
    else:
        logger.info("No SYNAPSE_PAT found. Server will run in standard OAuth mode only.")
