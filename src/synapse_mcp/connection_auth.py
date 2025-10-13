"""
Connection-scoped authentication for production multi-user support.

This module provides per-connection synapseclient management to ensure
user isolation and prevent cross-user data leakage in production deployments.

## Architecture

The auth_middleware extracts and validates OAuth tokens from the Authorization
header in every request, storing them in context. This module simply reads the
validated token from context and uses it to authenticate the synapseclient.

Flow:
1. Middleware extracts token from Authorization header
2. Middleware validates JWT (expiration, structure)
3. Middleware stores token in context state
4. This module reads token from context
5. This module authenticates synapseclient with the token
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


def _get_state(ctx: Context, key: str, default: Optional[Any] = None) -> Optional[Any]:
    getter = getattr(ctx, "get_state", None)
    if not callable(getter):
        return default
    try:
        value = getter(key)
    except (TypeError, AttributeError):
        # Unexpected signature; fall back if possible
        try:
            value = getter(key)  # type: ignore[misc]
        except Exception:  # pragma: no cover - safeguard
            return default
    except KeyError:
        return default
    if value is None and default is not None:
        return default
    return value


def _set_state(ctx: Context, key: str, value: Any) -> None:
    setter = getattr(ctx, "set_state", None)
    if not callable(setter):
        logger.debug("Context %s lacks set_state; unable to store %s", type(ctx).__name__, key)
        return
    try:
        setter(key, value)
    except TypeError:
        try:
            setter(key, value)  # type: ignore[misc]
        except Exception:  # pragma: no cover - defensive
            logger.debug("Context %s rejected set_state for %s", type(ctx).__name__, key)
            return


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
    logger.debug("get_synapse_client called with context type=%s attrs=%s", type(ctx).__name__, dir(ctx))
    client = _get_state(ctx, SYNAPSE_CLIENT_KEY)
    if client:
        logger.debug("Returning existing synapseclient for connection")
        return client

    # Create new client for this connection
    logger.info("Creating new synapseclient for connection")
    client = synapseclient.Synapse(cache_client=False)

    # Authenticate the client
    if not _authenticate_client(client, ctx):
        raise ConnectionAuthError("Authentication for connection needed (or re-authentication for expired sessions).")

    # Store client in connection context
    _set_state(ctx, SYNAPSE_CLIENT_KEY, client)
    _set_state(ctx, AUTH_INITIALIZED_KEY, True)

    logger.info("Successfully created and authenticated synapseclient for connection")
    return client

def _authenticate_client(client: synapseclient.Synapse, ctx: Context) -> bool:
    """
    Authenticate a synapseclient instance using available credentials.

    Priority order:
    1. PAT from environment variable (development)
    2. OAuth access token from FastMCP auth context (production)
    3. No authentication (public access only)

    Args:
        client: synapseclient instance to authenticate
        ctx: FastMCP context containing auth information

    Returns:
        bool: True if authentication succeeded, False otherwise
    """
    try:
        # Try PAT authentication first (development mode)
        if _try_pat_authentication(client, ctx):
            return True

        # Fall back to OAuth access token (production mode)
        if _try_oauth_authentication(client, ctx):
            return True

        # No authentication available - fail securely
        logger.error("No authentication credentials available - authentication required")
        return False

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

def _try_oauth_authentication(client: synapseclient.Synapse, ctx: Context) -> bool:
    """
    Try to authenticate using OAuth access token from context.

    The middleware has already extracted and validated the token from the
    Authorization header and stored it in context. We simply read it and
    use it to authenticate the synapseclient.
    """
    try:
        # Get token from context (middleware already validated and stored it)
        access_token = _get_state(ctx, "oauth_access_token")

        if not access_token:
            logger.debug("No OAuth access token found in context - middleware should have set it")
            return False

        # Authenticate using the access token
        client.login(authToken=access_token)

        # Get user profile to verify authentication
        profile = client.getUserProfile()

        # Store auth info in context
        _set_state(ctx, USER_AUTH_INFO_KEY, {
            "method": "oauth",
            "user_id": profile.get("ownerId"),
            "username": profile.get("userName"),
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
        _set_state(ctx, USER_AUTH_INFO_KEY, {
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
    return _get_state(ctx, USER_AUTH_INFO_KEY)

def is_authenticated(ctx: Context) -> bool:
    """
    Check if the current connection is authenticated.

    Args:
        ctx: FastMCP context object

    Returns:
        bool: True if connection is authenticated
    """
    value = _get_state(ctx, AUTH_INITIALIZED_KEY)
    return bool(value)

def require_authentication(ctx: Context) -> None:
    """
    Ensure the connection is authenticated, raise error if not.

    Args:
        ctx: FastMCP context object

    Raises:
        ConnectionAuthError: If connection is not authenticated
    """
    if not is_authenticated(ctx):
        raise ConnectionAuthError("Authentication for connection needed (or re-authentication for expired sessions).")

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
