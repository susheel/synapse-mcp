"""
Connection-scoped authentication for production multi-user support.

This module provides per-connection synapseclient management to ensure
user isolation and prevent cross-user data leakage in production deployments.

## Architecture

Authentication middleware (OAuthTokenMiddleware or PATAuthMiddleware) injects
tokens into the request context. This module retrieves tokens from context
and authenticates the synapseclient.

## OAuth Flow (Production):
1. OAuthTokenMiddleware extracts token from Authorization header
2. Middleware validates JWT (expiration, structure)
3. Middleware stores token in context: "oauth_access_token"
4. This module reads token from context
5. This module authenticates synapseclient with the token

## PAT Flow (Development):
1. PATAuthMiddleware loads SYNAPSE_PAT from environment at startup
2. Middleware injects token into context on each request: "synapse_pat_token"
3. This module reads token from context
4. This module authenticates synapseclient with the token
"""

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
    Authenticate a synapseclient instance using token from context.

    The appropriate middleware (OAuthTokenMiddleware or PATAuthMiddleware)
    has already injected the authentication token into the context.
    This function simply retrieves it and authenticates the client.

    Args:
        client: synapseclient instance to authenticate
        ctx: FastMCP context containing auth token

    Returns:
        bool: True if authentication succeeded, False otherwise
    """
    try:
        # Check for OAuth token (production mode)
        oauth_token = _get_state(ctx, "oauth_access_token")
        if oauth_token:
            return _authenticate_with_oauth(client, ctx, oauth_token)

        # Check for PAT token (development mode)
        pat_token = _get_state(ctx, "synapse_pat_token")
        if pat_token:
            return _authenticate_with_pat(client, ctx, pat_token)

        # No token found in context - fail securely
        logger.error("No authentication token found in context - authentication required")
        return False

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

def _authenticate_with_oauth(client: synapseclient.Synapse, ctx: Context, token: str) -> bool:
    """
    Authenticate synapseclient using OAuth access token.

    The OAuthTokenMiddleware has already validated this token and stored it in context.

    Args:
        client: synapseclient instance to authenticate
        ctx: FastMCP context for storing auth info
        token: Validated OAuth access token

    Returns:
        bool: True if authentication succeeded
    """
    try:
        # Authenticate using the access token
        client.login(authToken=token)

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
        logger.error(f"OAuth authentication failed: {e}")
        return False

def _authenticate_with_pat(client: synapseclient.Synapse, ctx: Context, token: str) -> bool:
    """
    Authenticate synapseclient using Personal Access Token.

    The PATAuthMiddleware has already loaded this token from environment and stored it in context.

    Args:
        client: synapseclient instance to authenticate
        ctx: FastMCP context for storing auth info
        token: PAT token from environment

    Returns:
        bool: True if authentication succeeded
    """
    try:
        # Authenticate using PAT
        client.login(authToken=token, silent=True)

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
        logger.error(f"PAT authentication failed: {e}")
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
