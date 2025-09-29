"""Public exports for the Synapse MCP package."""

from .app import auth, health_check, initialize_server, mcp
from .connection_auth import get_synapse_client
from .context_helpers import (
    ConnectionAuthError,
    first_successful_result,
    get_entity_operations,
    get_request_context,
    require_request_context,
)
from .resources import synapse_blog_feed
from .tools import (
    get_entity,
    get_entity_annotations,
    get_entity_children,
    search_synapse,
)

# Deprecated legacy helpers preserved for API compatibility

def initialize_authentication():
    """Deprecated placeholder for the old global authentication flow."""
    print("WARNING: initialize_authentication() is deprecated. Authentication is now per-connection.")
    return False, False


def authenticate_synapse_client(access_token: str):
    """Deprecated placeholder for the old global authentication flow."""
    print("WARNING: authenticate_synapse_client() is deprecated. Authentication is now per-connection.")
    return False


def is_authenticated():
    """Deprecated placeholder for the old global authentication flow."""
    print("WARNING: is_authenticated() is deprecated. Use connection_auth.is_authenticated(ctx) instead.")
    return False


def is_using_pat_auth():
    """Deprecated placeholder for the old global authentication flow."""
    print("WARNING: is_using_pat_auth() is deprecated. Check user_auth_info from connection context.")
    return False


__all__ = [
    "auth",
    "authenticate_synapse_client",
    "ConnectionAuthError",
    "first_successful_result",
    "get_entity",
    "get_entity_annotations",
    "get_entity_operations",
    "get_synapse_client",
    "get_request_context",
    "health_check",
    "initialize_authentication",
    "initialize_server",
    "is_authenticated",
    "is_using_pat_auth",
    "mcp",
    "require_request_context",
    "search_synapse",
    "synapse_blog_feed",
]
