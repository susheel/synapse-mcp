"""FastMCP middleware that copies OAuth tokens into the request context."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Optional, Sequence

from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger("synapse_mcp.auth_middleware")


@dataclass
class TokenBundle:
    token: str
    scopes: Sequence[str]
    subject: Optional[str]


class OAuthTokenMiddleware(Middleware):
    """Ensure FastMCP call contexts expose the current OAuth token."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        await self._store_auth_info(context)
        return await call_next(context)

    async def on_call_resource(self, context: MiddlewareContext, call_next):
        await self._store_auth_info(context)
        return await call_next(context)

    async def _store_auth_info(self, context: MiddlewareContext) -> None:
        fast_ctx = getattr(context, "fastmcp_context", None)
        logger.debug(
            "_store_auth_info invoked: context=%s fastmcp_context=%s",
            type(context).__name__,
            type(fast_ctx).__name__ if fast_ctx else None,
        )
        if fast_ctx is None:
            logger.debug("Skipping OAuth middleware: missing fastmcp_context")
            return

        bundle = await self._resolve_token_bundle(context, fast_ctx)
        if not bundle:
            logger.debug("No OAuth token available for this call")
            return

        session_id = getattr(fast_ctx, "session_id", None)
        logger.debug(
            "Resolved bundle -> token=%s*** subject=%s session_id=%s",
            bundle.token[:8],
            bundle.subject,
            session_id,
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
            if auth_proxy and hasattr(auth_proxy, "_session_tokens"):
                auth_proxy._session_tokens[session_id] = (bundle.token, bundle.subject)
                logger.debug(
                    "Recorded session token in proxy map: session=%s token=%s*** subject=%s",
                    session_id,
                    bundle.token[:8],
                    bundle.subject,
                )

    async def _resolve_token_bundle(self, context: MiddlewareContext, fast_ctx: Any) -> Optional[TokenBundle]:
        auth_ctx = getattr(context, "auth_context", None)
        if not auth_ctx:
            auth_ctx = getattr(fast_ctx, "auth_context", None)
        if auth_ctx:
            logger.debug(
                "auth_context available: type=%s attrs=%s",
                type(auth_ctx).__name__,
                dir(auth_ctx),
            )
        token_from_auth = getattr(auth_ctx, "token", None)
        if token_from_auth:
            logger.debug("Using token from auth_context")
            return TokenBundle(token=token_from_auth, scopes=[], subject=getattr(auth_ctx, "subject", None))

        header_bundle = _bundle_from_headers(context)
        if header_bundle:
            return header_bundle

        cached_bundle = _bundle_from_state(fast_ctx)
        if cached_bundle:
            return cached_bundle

        proxy_bundle = await _bundle_from_proxy(context, fast_ctx)
        if proxy_bundle:
            return proxy_bundle

        return None


def _bundle_from_headers(context: MiddlewareContext) -> Optional[TokenBundle]:
    message = getattr(context, "message", None)
    headers = getattr(message, "headers", {}) if message else {}
    auth_header = headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        logger.debug("Using Authorization header bearer token")
        return TokenBundle(token=token, scopes=[], subject=None)
    return None


def _get_state(fast_ctx: Any, key: str, default: Optional[Any] = None) -> Optional[Any]:
    getter = getattr(fast_ctx, "get_state", None)
    if not callable(getter):
        return default
    try:
        value = getter(key)
    except TypeError:
        try:
            value = getter(key)  # type: ignore[misc]
        except Exception:  # pragma: no cover - defensive
            return default
    except KeyError:
        return default
    if value is None and default is not None:
        return default
    return value


def _bundle_from_state(fast_ctx: Any) -> Optional[TokenBundle]:
    token = _get_state(fast_ctx, "oauth_access_token")
    if not token:
        return None
    scopes = _get_state(fast_ctx, "token_scopes") or []
    subject = _get_state(fast_ctx, "user_subject")
    logger.debug("Using cached OAuth token from context state")
    return TokenBundle(token=token, scopes=scopes, subject=subject)


async def _bundle_from_proxy(context: MiddlewareContext, fast_ctx: Any) -> Optional[TokenBundle]:
    server = getattr(fast_ctx, "fastmcp", None)
    auth_proxy = getattr(server, "auth", None) if server else None
    if not auth_proxy:
        return None

    access_tokens = list(getattr(auth_proxy, "_access_tokens", {}).keys())
    logger.debug(
        "Proxy bundle lookup: session_id=%s, proxy=%s, access_tokens=%s",
        getattr(fast_ctx, "session_id", None),
        type(auth_proxy).__name__,
        [tok[:8] + "***" for tok in access_tokens],
    )

    # Preferred path: dedicated helper on session-aware proxy
    token = None
    subject = None
    if hasattr(auth_proxy, "get_token_for_current_user"):
        token_result = await auth_proxy.get_token_for_current_user()
        if token_result:
            token, subject = token_result
            logger.debug("Proxy current-user token resolved: %s*** subject=%s", token[:8], subject)

    # Fallback: if we know the subject already, reuse proxy's helper
    if token is None:
        subject = _get_state(fast_ctx, "user_subject")
        if subject and hasattr(auth_proxy, "get_user_token"):
            token = await auth_proxy.get_user_token(subject)
            if token:
                logger.debug("Proxy returned token for subject %s: %s***", subject, token[:8])

    # If still unresolved, rely on the proxy's token inventory
    session_id = getattr(fast_ctx, "session_id", None)

    if token is None and session_id and hasattr(auth_proxy, "get_session_token_info"):
        info = auth_proxy.get_session_token_info(session_id)
        if info:
            token, session_subject = info
            if session_subject:
                subject = session_subject
            logger.debug("Proxy session map resolved token: %s*** subject=%s", token[:8], session_subject)

    if token is None and hasattr(auth_proxy, "iter_user_tokens"):
        tokens = await auth_proxy.iter_user_tokens()
        logger.debug("Middleware observed proxy tokens: %s", [(sub, tok[:8] + "***") for sub, tok in tokens])
        if tokens:
            subject, token = tokens[0]
            logger.debug("Using first available proxy token: %s*** subject=%s", token[:8], subject)

    if token is None and session_id and hasattr(auth_proxy, "get_token_for_session"):
        session_result = await auth_proxy.get_token_for_session(session_id)
        if session_result:
            token, session_subject = session_result
            if session_subject:
                subject = session_subject
            logger.debug("Proxy get_token_for_session provided token: %s*** subject=%s", token[:8], session_subject)

    if not token:
        return None

    scopes = _get_state(fast_ctx, "token_scopes") or []

    logger.debug("Resolved OAuth token via proxy for subject: %s", subject)
    return TokenBundle(token=token, scopes=scopes, subject=subject)


__all__ = ["OAuthTokenMiddleware"]
