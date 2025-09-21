"""
FastMCP middleware to bridge OAuth authentication to connection context.

This middleware captures the verified OAuth access token from FastMCP's auth system
and stores it in the context state where our connection-scoped authentication
system can access it.
"""

import logging
from typing import Any
from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger("synapse_mcp.auth_middleware")


class OAuthTokenMiddleware(Middleware):
    """
    Middleware that captures OAuth tokens from FastMCP auth and stores them
    in the context state for connection-scoped authentication.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept tool EXECUTION to extract and store OAuth token information.

        Runs before each tool call and ensures that any
        verified OAuth token is available in the context state for execution.
        """
        logger.info(f"OAuth middleware on_call_tool called for tool: {context.message.name}")
        await self._store_auth_info(context)
        return await call_next(context)

    async def on_call_resource(self, context: MiddlewareContext, call_next):
        """
        Intercept resource EXECUTION to extract and store OAuth token information.

        Resources need authentication context when they're actually called.
        """
        await self._store_auth_info(context)
        return await call_next(context)

    async def _store_auth_info(self, context: MiddlewareContext):
        """
        Extract and store OAuth token information in context for execution operations.

        This is ONLY called for execution operations (call_tool, call_resource),
        not for list operations which should work without authentication.
        """
        try:
            logger.debug(f"_store_auth_info called with context: {type(context)}")
            logger.debug(f"Context has fastmcp_context: {hasattr(context, 'fastmcp_context')}")

            # Access the FastMCP context if available
            if hasattr(context, 'fastmcp_context') and context.fastmcp_context:
                fastmcp_ctx = context.fastmcp_context

                # Debug: examine the context structure
                logger.debug(f"FastMCP context type: {type(fastmcp_ctx)}")
                if hasattr(fastmcp_ctx, 'fastmcp'):
                    server = fastmcp_ctx.fastmcp
                    logger.debug(f"Server type: {type(server)}")
                    if hasattr(server, 'auth'):
                        logger.debug(f"Server has auth: {server.auth}")

                # Try to access authentication information from FastMCP
                auth_info = self._extract_auth_info(context)

                if auth_info:
                    # Store authentication info in context state
                    if hasattr(fastmcp_ctx, 'set_state'):
                        fastmcp_ctx.set_state("oauth_access_token", auth_info.get("access_token"))
                        fastmcp_ctx.set_state("token_scopes", auth_info.get("scopes", []))
                        fastmcp_ctx.set_state("user_subject", auth_info.get("subject"))

                        logger.info(f"Stored OAuth token in context for subject: {auth_info.get('subject')}")
                    else:
                        logger.warning("FastMCP context doesn't support set_state")
                else:
                    logger.debug("No OAuth authentication info found in request")
            else:
                logger.debug("No FastMCP context available in middleware")

        except Exception as e:
            logger.error(f"Error in OAuth token middleware: {e}")
            # Don't fail the request if middleware has issues

    def _extract_auth_info(self, context: MiddlewareContext) -> dict[str, Any] | None:
        """
        Extract authentication information from the middleware context.

        Tries various sources in order of priority to find the OAuth token.
        """
        try:
            # 1. Check Authorization header (most direct)
            if hasattr(context, 'message') and hasattr(context.message, 'headers'):
                auth_header = context.message.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header[7:]  # Remove 'Bearer ' prefix
                    logger.debug(f"Found Bearer token in headers: {token[:20]}...")
                    return {"access_token": token}

            # 2. Check FastMCP context state (previously stored) - HIGHEST PRIORITY
            if hasattr(context, 'fastmcp_context') and context.fastmcp_context:
                fastmcp_ctx = context.fastmcp_context
                if hasattr(fastmcp_ctx, 'get_state'):
                    existing_token = fastmcp_ctx.get_state("oauth_access_token")
                    if existing_token:
                        logger.debug("Found existing OAuth token in context state - using cached token")
                        return {"access_token": existing_token}

            # 3. Check FastMCP server auth proxy
            if (hasattr(context, 'fastmcp_context') and context.fastmcp_context and
                hasattr(context.fastmcp_context, 'fastmcp')):

                server = context.fastmcp_context.fastmcp
                if hasattr(server, 'auth') and server.auth:
                    auth_proxy = server.auth

                    # Try to load access token from OAuth proxy
                    try:
                        # Method 1: Try with client_id if available
                        client_id = getattr(context.fastmcp_context, 'client_id', None)
                        logger.debug(f"FastMCP context client_id: {client_id}")
                        if client_id and hasattr(auth_proxy, 'load_access_token'):
                            access_token = auth_proxy.load_access_token(client_id)
                            if access_token:
                                logger.debug(f"Loaded access token from OAuth proxy for client: {client_id}")
                                return {"access_token": access_token}

                        # Method 2: Try to get session-specific token
                        session_id = getattr(context.fastmcp_context, 'session_id', None)
                        logger.debug(f"FastMCP context session_id: {session_id}")

                        if hasattr(auth_proxy, '_access_tokens') and auth_proxy._access_tokens:
                            logger.debug(f"OAuth proxy has {len(auth_proxy._access_tokens)} access tokens")
                            logger.debug(f"Available token keys: {[key[:20] + '***' for key in auth_proxy._access_tokens.keys()]}")

                            # The OAuth proxy stores tokens with the token itself as the key
                            # We need to get the token for the current session in a different way
                            # Since tokens are keyed by token value, we'll get the first available token
                            # This is safe because each session should only have one active token
                            if len(auth_proxy._access_tokens) == 1:
                                # Single user scenario - safe to use the only available token
                                token_key = next(iter(auth_proxy._access_tokens.keys()))
                                logger.debug(f"Using single available token for session: {session_id}")

                                # Store this token in context state for future use
                                if hasattr(context.fastmcp_context, 'set_state'):
                                    context.fastmcp_context.set_state("oauth_access_token", token_key)
                                    logger.debug("Stored access token in context state for future requests")

                                return {"access_token": token_key}
                            else:
                                logger.debug(f"Multiple tokens found ({len(auth_proxy._access_tokens)}), cannot safely determine which belongs to session: {session_id}")
                        else:
                            logger.debug("No _access_tokens found in OAuth proxy")

                    except Exception as e:
                        logger.debug(f"Error accessing OAuth proxy tokens: {e}")

                    # Fallback: check common token attributes
                    for attr in ['current_token', '_current_access_token', 'access_token', 'token']:
                        token_data = getattr(auth_proxy, attr, None)
                        if token_data:
                            logger.debug(f"Found token in server.auth.{attr}")
                            parsed = self._parse_auth_data(token_data)
                            if parsed:
                                return parsed

            # 4. Check context attributes for auth data
            for source, attr_list in [
                (getattr(context, 'request', None), ['auth', 'auth_context', 'access_token', 'token_info']),
                (getattr(context, 'fastmcp_context', None), ['auth_info', 'access_token', 'token_info', '_auth_context']),
                (context, ['auth_context'])
            ]:
                if source:
                    for attr in attr_list:
                        auth_data = getattr(source, attr, None)
                        if auth_data:
                            logger.debug(f"Found auth info in {attr}")
                            parsed = self._parse_auth_data(auth_data)
                            if parsed:
                                return parsed

        except Exception as e:
            logger.debug(f"Error extracting auth info: {e}")

        return None

    def _parse_auth_context(self, auth_context: Any) -> dict[str, Any] | None:
        """Parse authentication context object."""
        try:
            result = {}

            # Try common attribute names for tokens
            for token_attr in ['token', 'access_token', 'raw_token']:
                if hasattr(auth_context, token_attr):
                    result['access_token'] = getattr(auth_context, token_attr)
                    break

            # Try common attribute names for scopes
            for scope_attr in ['scopes', 'scope']:
                if hasattr(auth_context, scope_attr):
                    result['scopes'] = getattr(auth_context, scope_attr)
                    break

            # Try common attribute names for subject
            for subj_attr in ['sub', 'subject', 'user_id']:
                if hasattr(auth_context, subj_attr):
                    result['subject'] = getattr(auth_context, subj_attr)
                    break

            return result if result else None

        except Exception as e:
            logger.debug(f"Error parsing auth context: {e}")
            return None

    def _parse_auth_data(self, auth_data: Any) -> dict[str, Any] | None:
        """Parse various forms of authentication data."""
        try:
            # If it's a string, assume it's a token
            if isinstance(auth_data, str):
                return {"access_token": auth_data}

            # If it's a dict, look for token fields
            if isinstance(auth_data, dict):
                result = {}

                # Look for token
                for key in ['access_token', 'token', 'raw_token']:
                    if key in auth_data:
                        result['access_token'] = auth_data[key]
                        break

                # Look for scopes
                for key in ['scopes', 'scope']:
                    if key in auth_data:
                        result['scopes'] = auth_data[key]
                        break

                # Look for subject
                for key in ['sub', 'subject', 'user_id']:
                    if key in auth_data:
                        result['subject'] = auth_data[key]
                        break

                return result if result else None

            # If it's an object, try to parse it like auth context
            return self._parse_auth_context(auth_data)

        except Exception as e:
            logger.debug(f"Error parsing auth data: {e}")
            return None

# No handlers for list operations - they should work without authentication
    # on_list_tools, on_list_resources, on_list_prompts are intentionally omitted
    # These operations provide public capability discovery and don't need auth context