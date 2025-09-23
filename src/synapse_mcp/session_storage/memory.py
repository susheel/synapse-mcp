"""In-memory session storage for development and testing."""

from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Optional, Set

from .base import SessionStorage

logger = logging.getLogger("synapse_mcp.session_storage")


class InMemorySessionStorage(SessionStorage):
    """Fallback in-memory user-subject-based storage for development."""

    def __init__(self, *, max_tokens: Optional[int] = None, warn_fraction: float = 0.8) -> None:
        self._user_tokens: dict[str, str] = {}
        self._token_users: dict[str, str] = {}
        self._token_metadata: dict[str, dict[str, str]] = {}
        self._max_tokens = max_tokens if max_tokens and max_tokens > 0 else None
        self._warn_fraction = warn_fraction if 0 < warn_fraction < 1 else 0.8
        self._warned_high_water = False
        self._warned_capacity = False

    async def set_user_token(self, user_subject: str, access_token: str, ttl_seconds: int = 3600) -> None:
        now_utc = datetime.now(timezone.utc)
        metadata = {
            "created_at": now_utc.isoformat(),
            "expires_at": (now_utc + timedelta(seconds=ttl_seconds)).isoformat(),
            "user_subject": user_subject,
        }

        old_token = self._user_tokens.get(user_subject)
        if old_token:
            self._token_users.pop(old_token, None)
            self._token_metadata.pop(old_token, None)

        self._user_tokens[user_subject] = access_token
        self._token_users[access_token] = user_subject
        self._token_metadata[access_token] = metadata

        logger.debug("Stored user %s -> token %s*** in memory", user_subject, access_token[:20])
        self._emit_usage_warnings()

    async def get_user_token(self, user_subject: str) -> Optional[str]:
        return self._user_tokens.get(user_subject)

    async def remove_user_token(self, user_subject: str) -> None:
        access_token = self._user_tokens.pop(user_subject, None)
        if access_token:
            self._token_users.pop(access_token, None)
            self._token_metadata.pop(access_token, None)
            logger.debug("Removed user %s from memory", user_subject)
        self._emit_usage_warnings(triggered_by_removal=True)

    async def cleanup_expired_tokens(self) -> None:
        current_time = datetime.now(timezone.utc)
        expired_tokens = []

        for access_token, metadata in list(self._token_metadata.items()):
            try:
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if expires_at < current_time:
                    expired_tokens.append(access_token)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Error processing token metadata: %s", exc)
                expired_tokens.append(access_token)

        for access_token in expired_tokens:
            user_subject = self._token_users.get(access_token)
            if user_subject:
                await self.remove_user_token(user_subject)

        if expired_tokens:
            logger.info("Cleaned up %s expired tokens from memory", len(expired_tokens))
        else:
            # Ensure usage flags stay accurate even when no tokens expired
            self._emit_usage_warnings(triggered_by_removal=True)

    async def get_all_user_subjects(self) -> Set[str]:
        return set(self._user_tokens.keys())

    async def find_user_by_token(self, access_token: str) -> Optional[str]:
        return self._token_users.get(access_token)

    def _emit_usage_warnings(self, *, triggered_by_removal: bool = False) -> None:
        count = len(self._user_tokens)
        if self._max_tokens is None:
            return

        warn_threshold = max(1, math.ceil(self._max_tokens * self._warn_fraction))

        if count < warn_threshold:
            self._warned_high_water = False
        if count < self._max_tokens:
            self._warned_capacity = False

        if triggered_by_removal:
            return

        if not self._warned_high_water and warn_threshold <= count < self._max_tokens:
            logger.warning(
                "In-memory session storage nearing capacity: %s/%s tokens in use (>= %s%% threshold)",
                count,
                self._max_tokens,
                int(self._warn_fraction * 100),
            )
            self._warned_high_water = True

        if not self._warned_capacity and count >= self._max_tokens:
            logger.error(
                "In-memory session storage reached configured maximum of %s tokens; consider enabling Redis",
                self._max_tokens,
            )
            self._warned_capacity = True


__all__ = ["InMemorySessionStorage"]
