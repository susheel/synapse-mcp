"""FastMCP OAuth proxy extensions for Synapse."""

import logging
from typing import Any, Optional

from fastmcp.server.auth import OAuthProxy

from ..session_storage import create_session_storage

logger = logging.getLogger("synapse_mcp.oauth")


class SessionAwareOAuthProxy(OAuthProxy):
    """OAuth proxy that mirrors tokens into session storage."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session_storage = create_session_storage()
        self._session_tokens: dict[str, tuple[str, Optional[str]]] = {}
        self._code_sessions: dict[str, str] = {}
        logger.debug("SessionAwareOAuthProxy initialized with session storage %s", type(self._session_storage).__name__)

    async def _handle_idp_callback(self, request, *args, **kwargs):
        session_id = _extract_session_id(request)
        if session_id:
            logger.debug("OAuth callback processing for session: %s", session_id)

        existing_tokens = set(getattr(self, "_access_tokens", {}).keys())
        existing_codes = set(getattr(self, "_client_codes", {}).keys())
        result = await super()._handle_idp_callback(request, *args, **kwargs)
        if result:
            if session_id:
                client_codes = getattr(self, "_client_codes", {})
                new_codes = [code for code in client_codes if code not in existing_codes]
                for code in new_codes:
                    self._code_sessions[code] = session_id
                    logger.debug("Cached authorization code %s for session %s", code[:8], session_id)
            try:
                await self._map_new_tokens_to_users()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to map tokens to users: %s", exc)

            if session_id:
                access_tokens = getattr(self, "_access_tokens", {})
                new_tokens = [token for token in access_tokens if token not in existing_tokens]
                logger.debug(
                    "Session %s received %d new tokens (existing=%d)",
                    session_id,
                    len(new_tokens),
                    len(existing_tokens),
                )
                for token_key in new_tokens:
                    subject = await self._session_storage.find_user_by_token(token_key)
                    self._session_tokens[session_id] = (token_key, subject)
                    logger.debug(
                        "Associated session %s with token %s*** (subject=%s)",
                        session_id,
                        token_key[:20],
                        subject,
                    )
        return result

    async def exchange_authorization_code(
        self,
        client: Any,
        authorization_code: Any,
    ):
        existing_tokens = set(getattr(self, "_access_tokens", {}).keys())
        token_response = await super().exchange_authorization_code(client, authorization_code)

        try:
            await self._map_new_tokens_to_users()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to map tokens to users after exchange: %s", exc)

        access_tokens = getattr(self, "_access_tokens", {})
        new_tokens = [token for token in access_tokens if token not in existing_tokens]

        session_id = self._code_sessions.pop(authorization_code.code, None)
        if session_id:
            token_key: Optional[str] = None
            if new_tokens:
                token_key = new_tokens[-1]
            else:
                token_key = next((token for token, data in access_tokens.items() if data.client_id == client.client_id), None)

            if token_key:
                subject = await self._session_storage.find_user_by_token(token_key)
                self._session_tokens[session_id] = (token_key, subject)
                logger.debug(
                    "Associated session %s with token %s*** (subject=%s) via code exchange",
                    session_id,
                    token_key[:20],
                    subject,
                )
            else:
                logger.debug("No access token recorded for session %s during code exchange", session_id)

        return token_response

    async def _map_new_tokens_to_users(self) -> None:
        existing_users = await self._session_storage.get_all_user_subjects()
        access_tokens = getattr(self, "_access_tokens", {})
        known_attrs = [attr for attr in dir(self) if "token" in attr.lower() and not attr.startswith("__")]
        logger.debug(
            "_map_new_tokens_to_users: existing_users=%s tokens=%s token_attrs=%s",
            existing_users,
            [t[:8] + "***" for t in access_tokens],
            {attr: _summarize_token_attr(attr, getattr(self, attr, None)) for attr in known_attrs},
        )
        unmapped_tokens = [token for token in access_tokens if await self._session_storage.find_user_by_token(token) is None]

        for token_key in unmapped_tokens:
            try:
                import jwt

                decoded = jwt.decode(token_key, options={"verify_signature": False})
                user_subject = decoded.get("sub")
                if user_subject:
                    await self._session_storage.set_user_token(user_subject, token_key, ttl_seconds=3600)
                    logger.info("Mapped token %s*** to user %s", token_key[:20], user_subject)
                else:
                    logger.warning("Token %s*** has no subject claim", token_key[:20])
            except Exception as exc:  # pragma: no cover - decoding failures
                logger.warning("Failed to decode token %s***: %s", token_key[:20], exc)

    async def get_user_token(self, user_subject: str) -> Optional[str]:
        token_key = await self._session_storage.get_user_token(user_subject)
        if token_key and token_key in self._access_tokens:
            return token_key
        return None

    async def cleanup_user_tokens(self, user_subject: str) -> None:
        token_key = await self._session_storage.get_user_token(user_subject)
        if token_key:
            if token_key in self._access_tokens:
                del self._access_tokens[token_key]
            await self._session_storage.remove_user_token(user_subject)
            logger.info("Cleaned up token for user %s", user_subject)
            for session_id, (mapped_token, _) in list(self._session_tokens.items()):
                if mapped_token == token_key:
                    self._session_tokens.pop(session_id, None)

    async def cleanup_expired_tokens(self) -> None:
        await self._session_storage.cleanup_expired_tokens()

        existing_users = await self._session_storage.get_all_user_subjects()
        mapped_tokens = {
            token
            for user_subject in existing_users
            for token in [await self._session_storage.get_user_token(user_subject)]
            if token
        }

        orphaned = [token for token in list(self._access_tokens.keys()) if token not in mapped_tokens]
        for token in orphaned:
            if self._is_token_old_enough_to_cleanup(token):
                del self._access_tokens[token]

        if orphaned:
            logger.info("Cleaned up %s orphaned tokens from OAuth proxy", len(orphaned))
            for session_id, (mapped_token, _) in list(self._session_tokens.items()):
                if mapped_token in orphaned:
                    self._session_tokens.pop(session_id, None)

    def _is_token_old_enough_to_cleanup(self, token: str, min_age_seconds: int = 30) -> bool:
        try:
            import jwt
            from datetime import datetime, timezone

            decoded = jwt.decode(token, options={"verify_signature": False})
            issued_at = decoded.get("iat")
            if not issued_at:
                return True
            token_age = datetime.now(timezone.utc).timestamp() - issued_at
            if token_age <= min_age_seconds:
                logger.debug("Token is only %.1fs old, keeping for now", token_age)
                return False
            return True
        except Exception as exc:  # pragma: no cover - decoding failures
            logger.debug("Error checking token age, assuming old enough: %s", exc)
            return True

    async def iter_user_tokens(self) -> list[tuple[str, str]]:
        """Return all known (subject, token) pairs from storage."""

        tokens: list[tuple[str, str]] = []
        subjects = await self._session_storage.get_all_user_subjects()
        for subject in subjects:
            token = await self._session_storage.get_user_token(subject)
            if token:
                tokens.append((subject, token))
        logger.debug("iter_user_tokens -> %s", [(sub, tok[:8] + "***") for sub, tok in tokens])
        return tokens

    async def get_token_for_current_user(self) -> Optional[tuple[str, Optional[str]]]:
        """Return a token/subject pair when a single active user is known."""

        tokens = await self.iter_user_tokens()
        if len(tokens) == 1:
            subject, token = tokens[0]
            return token, subject
        return None

    def get_session_token_info(self, session_id: str) -> Optional[tuple[str, Optional[str]]]:
        info = self._session_tokens.get(session_id)
        logger.debug("get_session_token_info(%s) -> %s", session_id, (info[0][:8] + "***", info[1]) if info else None)
        return info

    async def get_token_for_session(self, session_id: str) -> Optional[tuple[str, Optional[str]]]:
        info = self.get_session_token_info(session_id)
        if info:
            return info
        subjects = await self._session_storage.get_all_user_subjects()
        logger.debug("get_token_for_session fallback subjects=%s", subjects)
        return None


def _extract_session_id(request) -> Optional[str]:
    try:
        if hasattr(request, "headers"):
            session_id = request.headers.get("mcp-session-id")
            if session_id:
                return session_id
        if hasattr(request, "state"):
            session_context = getattr(request.state, "session_context", None)
            if session_context and hasattr(session_context, "session_id"):
                return session_context.session_id
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not extract session ID from callback: %s", exc)
    return None


def _mask_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return token
    return token[:8] + "***"


def _summarize_token_attr(attr: str, value: Any) -> Any:
    if value is None:
        return None

    if attr == "_access_tokens" and isinstance(value, dict):
        summary: dict[str, dict[str, Any]] = {}
        for token, data in value.items():
            masked = _mask_token(token) or "<missing>"
            summary[masked] = {
                "client_id": getattr(data, "client_id", None),
                "scopes": getattr(data, "scopes", None),
                "expires_at": getattr(data, "expires_at", None),
            }
        return summary

    if attr == "_refresh_tokens" and isinstance(value, dict):
        summary = {}
        for token, data in value.items():
            masked = _mask_token(token) or "<missing>"
            summary[masked] = {
                "client_id": getattr(data, "client_id", None),
                "scopes": getattr(data, "scopes", None),
            }
        return summary

    if attr == "_session_tokens" and isinstance(value, dict):
        return {
            session: {"token": _mask_token(token), "subject": subject}
            for session, (token, subject) in value.items()
        }

    if isinstance(value, dict):
        return {"type": "dict", "count": len(value)}

    if isinstance(value, (list, set, tuple)):
        return {"type": type(value).__name__, "count": len(value)}

    return type(value).__name__


__all__ = ["SessionAwareOAuthProxy"]
