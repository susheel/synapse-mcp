"""Redis-backed session storage for production deployments."""

import asyncio
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

        self.user_token_key = f"{key_prefix}:user_token"
        self.token_user_key = f"{key_prefix}:token_user"
        self.token_metadata_key = f"{key_prefix}:metadata"

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

            async with redis_client.pipeline() as pipe:
                await pipe.hset(self.user_token_key, user_subject, access_token)
                await pipe.expire(self.user_token_key, ttl_seconds + 300)

                await pipe.hset(self.token_user_key, access_token, user_subject)
                await pipe.expire(self.token_user_key, ttl_seconds + 300)

                await pipe.hset(self.token_metadata_key, access_token, json.dumps(metadata))
                await pipe.expire(self.token_metadata_key, ttl_seconds + 300)

                await pipe.execute()

            logger.debug("Stored user %s -> token %s*** in Redis", user_subject, access_token[:20])

        except Exception as exc:  # pragma: no cover - network failure
            logger.error("Failed to store user token in Redis: %s", exc)
            raise

    async def get_user_token(self, user_subject: str) -> Optional[str]:
        try:
            redis_client = await self._get_redis()
            access_token = await redis_client.hget(self.user_token_key, user_subject)
            if access_token:
                logger.debug("Retrieved token for user %s from Redis", user_subject)
            return access_token
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to get user token from Redis: %s", exc)
            return None

    async def remove_user_token(self, user_subject: str) -> None:
        try:
            redis_client = await self._get_redis()
            access_token = await redis_client.hget(self.user_token_key, user_subject)
            if access_token:
                async with redis_client.pipeline() as pipe:
                    await pipe.hdel(self.user_token_key, user_subject)
                    await pipe.hdel(self.token_user_key, access_token)
                    await pipe.hdel(self.token_metadata_key, access_token)
                    await pipe.execute()
                logger.debug("Removed user %s and token %s*** from Redis", user_subject, access_token[:20])
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to remove user token from Redis: %s", exc)

    async def cleanup_expired_tokens(self) -> None:
        try:
            redis_client = await self._get_redis()
            all_metadata = await redis_client.hgetall(self.token_metadata_key)

            current_time = datetime.now(timezone.utc)
            expired_tokens: list[str] = []

            for access_token, metadata_json in all_metadata.items():
                try:
                    metadata = json.loads(metadata_json)
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if expires_at < current_time:
                        expired_tokens.append(access_token)
                        user_subject = metadata.get("user_subject")
                        if user_subject:
                            await self.remove_user_token(user_subject)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Error processing token metadata: %s", exc)
                    expired_tokens.append(access_token)

            if expired_tokens:
                logger.info("Cleaned up %s expired tokens from Redis", len(expired_tokens))

        except Exception as exc:  # pragma: no cover
            logger.error("Failed to cleanup expired tokens in Redis: %s", exc)

    async def get_all_user_subjects(self) -> Set[str]:
        try:
            redis_client = await self._get_redis()
            user_subjects = await redis_client.hkeys(self.user_token_key)
            return set(user_subjects)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to get all user subjects from Redis: %s", exc)
            return set()

    async def find_user_by_token(self, access_token: str) -> Optional[str]:
        try:
            redis_client = await self._get_redis()
            return await redis_client.hget(self.token_user_key, access_token)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to find user by token in Redis: %s", exc)
            return None

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            logger.debug("Redis connection closed")


__all__ = ["RedisSessionStorage", "REDIS_AVAILABLE"]
