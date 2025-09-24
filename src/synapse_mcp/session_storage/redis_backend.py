"""Redis-backed session storage for production deployments."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

from .base import SessionStorage

logger = logging.getLogger("synapse_mcp.session_storage")

try:  # pragma: no cover - import guarded by runtime availability
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when redis is absent
    redis = None  # type: ignore
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - falling back to in-memory storage")


class RedisSessionStorage(SessionStorage):
    """Redis-based session storage for production deployments."""

    def __init__(self, redis_url: str, key_prefix: str = "synapse_mcp:session") -> None:
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis dependency not available")

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis: Optional["redis.Redis"] = None

        self.user_subjects_set = f"{key_prefix}:subjects"
        self.known_tokens_set = f"{key_prefix}:tokens"

    def _subject_token_key(self, user_subject: str) -> str:
        return f"{self.key_prefix}:user:{user_subject}"

    def _token_subject_key(self, access_token: str) -> str:
        return f"{self.key_prefix}:token:{access_token}"

    def _token_metadata_key(self, access_token: str) -> str:
        return f"{self.key_prefix}:metadata:{access_token}"

    async def _get_redis(self) -> "redis.Redis":
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30,
                )
                await self._redis.ping()
                logger.info("Redis connection established")
            except Exception as exc:  # pragma: no cover - connection failure
                logger.error("Failed to connect to Redis: %s", exc)
                raise
        return self._redis

    async def set_user_token(self, user_subject: str, access_token: str, ttl_seconds: int = 3600) -> None:
        try:
            redis_client = await self._get_redis()

            now_utc = datetime.now(timezone.utc)
            metadata = {
                "created_at": now_utc.isoformat(),
                "expires_at": (now_utc + timedelta(seconds=ttl_seconds)).isoformat(),
                "user_subject": user_subject,
            }

            existing_token = await redis_client.get(self._subject_token_key(user_subject))
            if existing_token and existing_token != access_token:
                await self._delete_token_index(redis_client, existing_token)

            async with redis_client.pipeline() as pipe:
                pipe.setex(self._subject_token_key(user_subject), ttl_seconds, access_token)
                pipe.setex(self._token_subject_key(access_token), ttl_seconds, user_subject)
                pipe.setex(self._token_metadata_key(access_token), ttl_seconds, json.dumps(metadata))

                pipe.sadd(self.user_subjects_set, user_subject)
                pipe.sadd(self.known_tokens_set, access_token)
                await pipe.execute()

            logger.debug("Stored user %s -> token %s*** in Redis", user_subject, access_token[:20])

        except Exception as exc:  # pragma: no cover - network failure
            logger.error("Failed to store user token in Redis: %s", exc)
            raise

    async def get_user_token(self, user_subject: str) -> Optional[str]:
        try:
            redis_client = await self._get_redis()
            access_token = await redis_client.get(self._subject_token_key(user_subject))
            if access_token:
                logger.debug("Retrieved token for user %s from Redis", user_subject)
                await redis_client.sadd(self.user_subjects_set, user_subject)
            return access_token
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to get user token from Redis: %s", exc)
            return None

    async def remove_user_token(self, user_subject: str) -> None:
        try:
            redis_client = await self._get_redis()
            subject_key = self._subject_token_key(user_subject)
            access_token = await redis_client.get(subject_key)

            await redis_client.delete(subject_key)
            await redis_client.srem(self.user_subjects_set, user_subject)

            if access_token:
                await self._delete_token_index(redis_client, access_token)
                logger.debug("Removed user %s and token %s*** from Redis", user_subject, access_token[:20])
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to remove user token from Redis: %s", exc)

    async def cleanup_expired_tokens(self) -> None:
        try:
            redis_client = await self._get_redis()
            removed_subjects = await self._scan_and_clean_set(
                redis_client,
                self.user_subjects_set,
                self._subject_token_key,
            )
            removed_tokens = await self._scan_and_clean_set(
                redis_client,
                self.known_tokens_set,
                self._token_subject_key,
            )

            if removed_subjects or removed_tokens:
                logger.info(
                    "Cleaned up %s subjects and %s tokens from Redis session storage",
                    removed_subjects,
                    removed_tokens,
                )

        except Exception as exc:  # pragma: no cover
            logger.error("Failed to cleanup expired tokens in Redis: %s", exc)

    async def get_all_user_subjects(self) -> Set[str]:
        try:
            redis_client = await self._get_redis()
            live_subjects: Set[str] = set()
            async for batch_members, existence in self._iter_live_members(
                redis_client,
                self.user_subjects_set,
                self._subject_token_key,
            ):
                live_subjects.update(member for member, exists in zip(batch_members, existence) if exists)
            return live_subjects
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to get all user subjects from Redis: %s", exc)
            return set()

    async def find_user_by_token(self, access_token: str) -> Optional[str]:
        try:
            redis_client = await self._get_redis()
            return await redis_client.get(self._token_subject_key(access_token))
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to find user by token in Redis: %s", exc)
            return None

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            logger.debug("Redis connection closed")

    async def _delete_token_index(self, redis_client: "redis.Redis", access_token: str) -> None:
        async with redis_client.pipeline() as pipe:
            pipe.delete(self._token_subject_key(access_token))
            pipe.delete(self._token_metadata_key(access_token))
            pipe.srem(self.known_tokens_set, access_token)
            await pipe.execute()

    async def _scan_and_clean_set(
        self,
        redis_client: "redis.Redis",
        set_key: str,
        key_formatter,
        *,
        batch_size: int = 100,
    ) -> int:
        removed_total = 0
        cursor = 0
        while True:
            cursor, members = await redis_client.sscan(set_key, cursor=cursor, count=batch_size)
            if members:
                keys_to_check = [key_formatter(member) for member in members]
                async with redis_client.pipeline() as pipe:
                    for key in keys_to_check:
                        pipe.exists(key)
                    existence_results = await pipe.execute()

                expired_members = [member for member, exists in zip(members, existence_results) if not exists]
                if expired_members:
                    await redis_client.srem(set_key, *expired_members)
                    removed_total += len(expired_members)

            if cursor == 0:
                break
        return removed_total

    async def _iter_live_members(
        self,
        redis_client: "redis.Redis",
        set_key: str,
        key_formatter,
        *,
        batch_size: int = 100,
    ):
        cursor = 0
        while True:
            cursor, members = await redis_client.sscan(set_key, cursor=cursor, count=batch_size)
            if members:
                keys_to_check = [key_formatter(member) for member in members]
                async with redis_client.pipeline() as pipe:
                    for key in keys_to_check:
                        pipe.exists(key)
                    existence_results = await pipe.execute()

                expired_members = [member for member, exists in zip(members, existence_results) if not exists]
                if expired_members:
                    await redis_client.srem(set_key, *expired_members)

                yield members, existence_results

            if cursor == 0:
                break


__all__ = ["RedisSessionStorage", "REDIS_AVAILABLE"]
