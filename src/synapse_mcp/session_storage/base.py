"""Abstract session storage definitions."""

import abc
from typing import Optional, Set


class SessionStorage(abc.ABC):
    """Abstract base class for user-subject token storage."""

    @abc.abstractmethod
    async def set_user_token(self, user_subject: str, access_token: str, ttl_seconds: int = 3600) -> None:
        """Store a user-subject to access-token mapping."""

    @abc.abstractmethod
    async def get_user_token(self, user_subject: str) -> Optional[str]:
        """Return the access token for ``user_subject`` if available."""

    @abc.abstractmethod
    async def remove_user_token(self, user_subject: str) -> None:
        """Remove the mapping for ``user_subject`` if it exists."""

    @abc.abstractmethod
    async def cleanup_expired_tokens(self) -> None:
        """Purge expired tokens from storage."""

    @abc.abstractmethod
    async def get_all_user_subjects(self) -> Set[str]:
        """Return the set of known user subjects."""

    @abc.abstractmethod
    async def find_user_by_token(self, access_token: str) -> Optional[str]:
        """Return the user subject associated with ``access_token`` if found."""


__all__ = ["SessionStorage"]
