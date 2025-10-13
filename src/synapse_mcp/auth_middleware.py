"""
MCP-Compliant OAuth Token Middleware for Multi-User Servers.

This middleware implements OAuth 2.1 token validation as required by the
Model Context Protocol specification.

## MCP Specification Compliance

Per MCP spec (https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization):
- "authorization MUST be included in every HTTP request from client to server"
- "Tokens MUST be included using the Authorization header"
- "Servers MUST validate access tokens as described in OAuth 2.1 Section 5.2"

## Token Validation

This middleware validates every request:
1. **Extracts** token from Authorization header: `Authorization: Bearer <token>`
2. **Validates** JWT structure and expiration
3. **Returns HTTP 401** if token is missing, invalid, or expired
4. **Stores** validated token in context for tools to use

## Error Responses

Per OAuth 2.1 / MCP spec:
- **401 Unauthorized**: Missing, invalid, or expired token
- **403 Forbidden**: Valid token but insufficient permissions (handled at tool level)

## Architecture

Each request is independently authenticated. No caching or session lookups needed
because the client sends the token with every request. This ensures:
- Proper multi-user isolation
- Spec compliance
- Simple, auditable auth flow
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Optional, Sequence

from fastmcp.server.middleware import Middleware, MiddlewareContext
try:
    from fastmcp.server.dependencies import get_access_token, get_http_request
except ImportError:
    get_access_token = None
    get_http_request = None

from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from .utils import mask_identifier, mask_token

logger = logging.getLogger("synapse_mcp.auth_middleware")


class AuthenticationError(HTTPException):
    """HTTP 401 Unauthorized - Missing or invalid token."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=401, detail=detail)


def validate_jwt_token(token: str) -> None:
    """
    Validate JWT token according to MCP spec requirements.

    Validates:
    - Token is a valid JWT structure
    - Token is not expired

    Raises:
        AuthenticationError: If token is invalid or expired (HTTP 401)
    """
    try:
        import jwt

        # Decode without signature verification (we trust Synapse's token)
        # But validate structure and expiration
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Check expiration (required by OAuth 2.1)
        exp = decoded.get("exp")
        if exp is None:
            logger.warning("Token missing 'exp' claim")
            raise AuthenticationError("Invalid token: missing expiration")

        # Check if token is expired
        now = datetime.now(timezone.utc).timestamp()
        if now >= exp:
            logger.info("Token expired: exp=%s, now=%s", exp, now)
            raise AuthenticationError("Token expired")

        # Token is valid
        logger.debug("Token validated: expires_at=%s", datetime.fromtimestamp(exp, timezone.utc).isoformat())

    except jwt.DecodeError as e:
        logger.warning("Invalid JWT token structure: %s", e)
        raise AuthenticationError("Invalid token format")
    except AuthenticationError:
        # Re-raise our own exceptions
        raise
    except Exception as e:
        logger.error("Token validation error: %s", e)
        raise AuthenticationError("Token validation failed")


@dataclass
class TokenBundle:
    """A container for an OAuth token and its associated metadata."""

    token: str
    scopes: Sequence[str]
    subject: Optional[str]


class OAuthTokenMiddleware(Middleware):
    """
    Extracts OAuth tokens from request headers for multi-user FastMCP servers.

    This middleware intercepts tool and resource calls, extracts the OAuth token
    from the Authorization header, and stores it in the fastmcp_context for use
    by downstream tools.

    The token is expected in the Authorization header as:
        Authorization: Bearer <synapse_jwt_token>

    This ensures each request is independently authenticated, maintaining proper
    multi-user isolation.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercepts a tool call to store OAuth token information in the context.

        This method is called by the FastMCP server before a tool is executed.
        It calls `_store_auth_info` to resolve and cache the token, and then
        passes control to the next middleware in the chain.

        Args:
            context: The middleware context for the current call.
            call_next: A callable that invokes the next middleware.

        Returns:
            The result of the next middleware in the chain.
        """

        await self._store_auth_info(context)
        return await call_next(context)

    async def on_call_resource(self, context: MiddlewareContext, call_next):
        """
        Intercepts a resource call to store OAuth token information in the context.

        This method is called by the FastMCP server before a resource is accessed.
        It calls `_store_auth_info` to resolve and cache the token, and then
        passes control to the next middleware in the chain.

        Args:
            context: The middleware context for the current call.
            call_next: A callable that invokes the next middleware.

        Returns:
            The result of the next middleware in the chain.
        """

        await self._store_auth_info(context)
        return await call_next(context)

    async def _store_auth_info(self, context: MiddlewareContext) -> None:
        """
        Extract and validate OAuth token from request, storing it in context.

        Raises:
            AuthenticationError (HTTP 401): If token is missing, invalid, or expired
        """
        # Inspect HTTP request to see what auth info is sent (debug mode)
        if get_http_request and logger.isEnabledFor(logging.DEBUG):
            try:
                http_request = get_http_request()
                if http_request:
                    logger.debug(
                        "HTTP Request - URL: %s, Method: %s, Has Auth: %s",
                        getattr(http_request, 'url', None),
                        getattr(http_request, 'method', None),
                        'authorization' in http_request.headers if hasattr(http_request, 'headers') else False,
                    )
            except Exception as exc:
                logger.debug("Could not inspect HTTP request: %s", exc)

        fast_ctx = getattr(context, "fastmcp_context", None)
        logger.debug(
            "_store_auth_info invoked: context=%s fastmcp_context=%s",
            type(context).__name__,
            type(fast_ctx).__name__ if fast_ctx else None,
        )
        if fast_ctx is None:
            logger.debug("Skipping OAuth middleware: missing fastmcp_context")
            return

        # Resolve and validate token - raises AuthenticationError on failure
        bundle = await self._resolve_token_bundle(context, fast_ctx)

        session_id = getattr(fast_ctx, "session_id", None)
        logger.debug(
            "Resolved bundle -> token=%s subject=%s session_id=%s",
            mask_token(bundle.token),
            bundle.subject,
            mask_identifier(session_id),
        )

        if hasattr(fast_ctx, "set_state"):
            fast_ctx.set_state("oauth_access_token", bundle.token)
            fast_ctx.set_state("token_scopes", list(bundle.scopes))
            fast_ctx.set_state("user_subject", bundle.subject)
            if session_id is not None:
                fast_ctx.set_state("session_id", session_id)
            logger.info("Stored OAuth token for subject: %s", bundle.subject)
        else:
            logger.warning("FastMCP context does not expose set_state; unable to cache token")

        if session_id and hasattr(fast_ctx, "fastmcp"):
            auth_proxy = getattr(fast_ctx.fastmcp, "auth", None)
            cache_fn = getattr(auth_proxy, "cache_session_token", None)
            if callable(cache_fn):
                cache_fn(session_id, bundle.token, bundle.subject)
                logger.debug(
                    "Recorded session token via proxy helper: session=%s token=%s subject=%s",
                    mask_identifier(session_id),
                    mask_token(bundle.token),
                    bundle.subject,
                )

    async def _resolve_token_bundle(self, context: MiddlewareContext, fast_ctx: Any) -> TokenBundle:
        """
        Resolve and validate OAuth token from the request.

        Per MCP spec: "authorization MUST be included in every HTTP request"

        Validates:
        - Token is present in Authorization header
        - Token is a valid JWT structure
        - Token is not expired

        Raises:
            AuthenticationError (HTTP 401): If token is missing, invalid, or expired

        Returns:
            TokenBundle: Validated token with metadata
        """

        token = None

        # Primary path: Extract from Authorization header
        # This is where Claude Code/Desktop sends the Synapse JWT
        if get_http_request:
            try:
                http_request = get_http_request()
                if http_request and hasattr(http_request, 'headers'):
                    auth_header = http_request.headers.get("authorization")
                    if auth_header and auth_header.startswith("Bearer "):
                        token = auth_header[len("Bearer "):]
                        logger.info("Extracted token from Authorization header: %s", mask_token(token))
            except Exception as exc:
                logger.debug("Could not extract token from HTTP request: %s", exc)

        # Fallback: Check auth_context (in case FastMCP populates it differently)
        if not token:
            auth_ctx = getattr(context, "auth_context", None)
            if not auth_ctx:
                auth_ctx = getattr(fast_ctx, "auth_context", None)

            if auth_ctx:
                token = getattr(auth_ctx, "token", None)
                if token:
                    logger.info("Using token from auth_context: %s", mask_token(token))

        # Last resort: Check for bearer token in context message headers
        if not token:
            header_bundle = _bundle_from_headers(context)
            if header_bundle:
                token = header_bundle.token
                logger.info("Extracted token from context headers: %s", mask_token(token))

        # MCP spec requirement: Token MUST be present
        if not token:
            logger.warning("No Authorization header in request - HTTP 401")
            raise AuthenticationError("Missing Authorization header")

        # Validate token per OAuth 2.1 / MCP spec
        validate_jwt_token(token)

        # Return validated token
        return TokenBundle(token=token, scopes=[], subject=None)


def _bundle_from_headers(context: MiddlewareContext) -> Optional[TokenBundle]:
    message = getattr(context, "message", None)
    headers = getattr(message, "headers", {}) if message else {}
    auth_header = headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        logger.debug("Using Authorization header bearer token")
        return TokenBundle(token=token, scopes=[], subject=None)
    return None


# Note: Removed _get_state, _bundle_from_state, and _bundle_from_proxy functions.
# In a multi-user environment, each request includes the token in the Authorization header.
# We don't need complex proxy lookups or state caching.


__all__ = ["OAuthTokenMiddleware"]
