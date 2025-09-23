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
SESSION_ID_KEY = "session_id"


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


def _extract_session_proxy(ctx: Context) -> tuple[Optional[str], Any]:
    session_id = _get_state(ctx, SESSION_ID_KEY)

    fast_ctx = getattr(ctx, "fastmcp_context", None)
    if fast_ctx is None:
        fast_ctx = getattr(ctx, "_fastmcp_context", None)
    if fast_ctx is None and hasattr(ctx, "context"):
        fast_ctx = getattr(ctx, "context", None)

    if session_id is None and fast_ctx is not None:
        session_id = getattr(fast_ctx, "session_id", None)

    auth_proxy = None
    server = getattr(fast_ctx, "fastmcp", None) if fast_ctx else None
    if server is not None:
        auth_proxy = getattr(server, "auth", None)

    logger.debug("_extract_session_proxy -> session_id=%s proxy=%s", session_id, type(auth_proxy).__name__ if auth_proxy else None)
    return session_id, auth_proxy

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
        raise ConnectionAuthError("Failed to authenticate synapseclient for this connection")

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
    Try to authenticate using OAuth access token from FastMCP auth context.

    In production with OAuth, FastMCP provides access token information
    through the auth system that we can use for Synapse authentication.
    """
    try:
        # FastMCP 2.0+ provides access token through context
        # The JWT verifier in auth.py should have stored the token
        access_token = _get_state(ctx, "oauth_access_token")
        logger.debug(f"Retrieved OAuth access token from context: {'***' if access_token else 'None'}")

        # Debug: check all context state keys
        if hasattr(ctx, '_state'):
            logger.debug(f"Context state keys: {list(ctx._state.keys()) if ctx._state else 'No state'}")
        else:
            logger.debug("Context has no _state attribute")

        # Fallback: try to get from auth context if available
        if not access_token:
            # FastMCP might store auth info differently
            auth_context = getattr(ctx, 'auth_context', None)
            if auth_context and hasattr(auth_context, 'token'):
                access_token = auth_context.token

        if not access_token:
            logger.debug("No OAuth access token found in context")
            session_id, auth_proxy = _extract_session_proxy(ctx)
            if session_id and auth_proxy and hasattr(auth_proxy, "get_session_token_info"):
                info = auth_proxy.get_session_token_info(session_id)
                if info:
                    access_token, subject_hint = info
                    logger.debug("Recovered token %s*** for session %s via proxy", access_token[:20], session_id)
                    _set_state(ctx, "oauth_access_token", access_token)
                    if subject_hint:
                        _set_state(ctx, "user_subject", subject_hint)
                else:
                    logger.debug("Proxy had no token for session %s", session_id)
            if not access_token:
                logger.debug("OAuth authentication still missing token after proxy lookup")
                return False

        # Authenticate using the access token
        client.login(authToken=access_token)

        # Get user profile to verify authentication
        profile = client.getUserProfile()

        # Store auth info in context
        scopes = _get_state(ctx, "token_scopes") or []
        _set_state(ctx, USER_AUTH_INFO_KEY, {
            "method": "oauth",
            "user_id": profile.get("ownerId"),
            "username": profile.get("userName"),
            "scopes": scopes
        })
        session_id, _ = _extract_session_proxy(ctx)
        if session_id:
            _set_state(ctx, SESSION_ID_KEY, session_id)
        logger.debug(
            "OAuth auth stored for subject=%s session_id=%s", profile.get("userName"), session_id
        )

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
