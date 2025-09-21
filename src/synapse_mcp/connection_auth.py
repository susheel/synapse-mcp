"""
Connection-scoped authentication for production multi-user support.

This module provides per-connection synapseclient management to ensure
user isolation and prevent cross-user data leakage in production deployments.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastmcp import Context
import synapseclient

logger = logging.getLogger("synapse_mcp.connection_auth")

# Constants for context state keys
SYNAPSE_CLIENT_KEY = "synapse_client"
USER_AUTH_INFO_KEY = "user_auth_info"
AUTH_INITIALIZED_KEY = "auth_initialized"

class ConnectionAuthError(Exception):
    """Raised when connection authentication fails."""
    pass

def get_synapse_client(ctx: Context) -> synapseclient.Synapse:
    """
    Get or create a synapseclient instance for this connection.

    This function ensures each connection has its own isolated synapseclient
    instance, preventing cross-user authentication issues and data leakage.

    Args:
        ctx: FastMCP context object for this connection

    Returns:
        synapseclient.Synapse: Authenticated client for this connection

    Raises:
        ConnectionAuthError: If authentication fails or is not configured
    """
    # Check if client already exists for this connection
    client = ctx.get_state(SYNAPSE_CLIENT_KEY)
    if client:
        logger.debug("Returning existing synapseclient for connection")
        return client

    # Create new client for this connection
    logger.info("Creating new synapseclient for connection")
    client = synapseclient.Synapse()

    # Authenticate the client
    if not _authenticate_client(client, ctx):
        raise ConnectionAuthError("Failed to authenticate synapseclient for this connection")

    # Store client in connection context
    ctx.set_state(SYNAPSE_CLIENT_KEY, client)
    ctx.set_state(AUTH_INITIALIZED_KEY, True)

    logger.info("Successfully created and authenticated synapseclient for connection")
    return client

def _authenticate_client(client: synapseclient.Synapse, ctx: Context) -> bool:
    """
    Authenticate a synapseclient instance using available credentials.

    Priority order:
    1. OAuth access token from FastMCP auth context (production)
    2. PAT from environment variable (development)
    3. No authentication (public access only)

    Args:
        client: synapseclient instance to authenticate
        ctx: FastMCP context containing auth information

    Returns:
        bool: True if authentication succeeded, False otherwise
    """
    try:
        # Try OAuth access token first (production mode)
        if _try_oauth_authentication(client, ctx):
            return True

        # Fall back to PAT authentication (development mode)
        if _try_pat_authentication(client, ctx):
            return True

        # No authentication available - public access only
        logger.warning("No authentication credentials available - using anonymous access")
        ctx.set_state(USER_AUTH_INFO_KEY, {
            "method": "anonymous",
            "user_id": None,
            "scopes": ["public"]
        })
        return True

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

def _try_oauth_authentication(client: synapseclient.Synapse, ctx: Context) -> bool:
    """
    Try to authenticate using OAuth access token from FastMCP auth context.

    In production with OAuth, FastMCP provides access token information
    through the auth system that we can use for Synapse authentication.
    """
    try:
        # FastMCP 2.0+ provides access token through context
        # The JWT verifier in auth.py should have stored the token
        access_token = ctx.get_state("oauth_access_token")

        # Fallback: try to get from auth context if available
        if not access_token:
            # FastMCP might store auth info differently
            auth_context = getattr(ctx, 'auth_context', None)
            if auth_context and hasattr(auth_context, 'token'):
                access_token = auth_context.token

        if not access_token:
            logger.debug("No OAuth access token found in context")
            return False

        # Authenticate using the access token
        client.login(authToken=access_token)

        # Get user profile to verify authentication
        profile = client.getUserProfile()

        # Store auth info in context
        ctx.set_state(USER_AUTH_INFO_KEY, {
            "method": "oauth",
            "user_id": profile.get("ownerId"),
            "username": profile.get("userName"),
            "scopes": ctx.get_state("token_scopes", [])
        })

        logger.info(f"OAuth authentication successful for user: {profile.get('userName')}")
        return True

    except Exception as e:
        logger.debug(f"OAuth authentication failed: {e}")
        return False

def _try_pat_authentication(client: synapseclient.Synapse, ctx: Context) -> bool:
    """
    Try to authenticate using Personal Access Token from environment.

    This is primarily for development and local testing scenarios.
    """
    try:
        synapse_pat = os.environ.get("SYNAPSE_PAT")
        if not synapse_pat:
            logger.debug("No SYNAPSE_PAT environment variable found")
            return False

        # Authenticate using PAT
        client.login(authToken=synapse_pat, silent=True)

        # Get user profile to verify authentication
        profile = client.getUserProfile()

        # Store auth info in context
        ctx.set_state(USER_AUTH_INFO_KEY, {
            "method": "pat",
            "user_id": profile.get("ownerId"),
            "username": profile.get("userName"),
            "scopes": ["full_access"]  # PATs have full access
        })

        logger.info(f"PAT authentication successful for user: {profile.get('userName')}")
        return True

    except Exception as e:
        logger.debug(f"PAT authentication failed: {e}")
        return False

def get_user_auth_info(ctx: Context) -> Optional[Dict[str, Any]]:
    """
    Get authentication information for the current connection.

    Args:
        ctx: FastMCP context object

    Returns:
        Dict containing user authentication information, or None if not authenticated
    """
    return ctx.get_state(USER_AUTH_INFO_KEY)

def is_authenticated(ctx: Context) -> bool:
    """
    Check if the current connection is authenticated.

    Args:
        ctx: FastMCP context object

    Returns:
        bool: True if connection is authenticated
    """
    return ctx.get_state(AUTH_INITIALIZED_KEY, False)

def require_authentication(ctx: Context) -> None:
    """
    Ensure the connection is authenticated, raise error if not.

    Args:
        ctx: FastMCP context object

    Raises:
        ConnectionAuthError: If connection is not authenticated
    """
    if not is_authenticated(ctx):
        raise ConnectionAuthError("This operation requires authentication")

def has_scope(ctx: Context, required_scope: str) -> bool:
    """
    Check if the authenticated user has a specific scope.

    Args:
        ctx: FastMCP context object
        required_scope: Scope to check for

    Returns:
        bool: True if user has the required scope
    """
    auth_info = get_user_auth_info(ctx)
    if not auth_info:
        return False

    user_scopes = auth_info.get("scopes", [])
    return required_scope in user_scopes or "full_access" in user_scopes