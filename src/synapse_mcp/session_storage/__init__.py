"""Session storage factory and exports."""

import asyncio
import logging
import os
from typing import Optional

from .base import SessionStorage
from .memory import InMemorySessionStorage
from .redis_backend import REDIS_AVAILABLE, RedisSessionStorage, redis as _redis_async

logger = logging.getLogger("synapse_mcp.session_storage")


def create_session_storage(env: Optional[dict[str, str]] = None) -> SessionStorage:
    """Create appropriate session storage based on configuration."""
    env = env or os.environ
    redis_url = env.get("REDIS_URL")

    if redis_url and REDIS_AVAILABLE:
        if _redis_connection_available(redis_url):
            logger.info("Using Redis session storage: %s", _redact_redis_url(redis_url))
            return RedisSessionStorage(redis_url)

        logger.warning(
            "Redis at %s unavailable - falling back to in-memory session storage",
            _redact_redis_url(redis_url),
        )
    elif redis_url and not REDIS_AVAILABLE:
        logger.warning("REDIS_URL provided but Redis not available - using in-memory storage")

    max_tokens = _parse_int(env.get("SYNAPSE_MCP_MEMORY_SESSION_MAX_TOKENS"), "SYNAPSE_MCP_MEMORY_SESSION_MAX_TOKENS")
    warn_fraction = _parse_float(env.get("SYNAPSE_MCP_MEMORY_SESSION_WARN_FRACTION"), "SYNAPSE_MCP_MEMORY_SESSION_WARN_FRACTION", default=0.8)

    logger.info(
        "Using in-memory session storage (max_tokens=%s warn_fraction=%.2f)",
        max_tokens,
        warn_fraction,
    )

    return InMemorySessionStorage(max_tokens=max_tokens, warn_fraction=warn_fraction)


def _redis_connection_available(redis_url: str) -> bool:
    if not REDIS_AVAILABLE or _redis_async is None:
        return False

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        client = _redis_async.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        try:
            loop.run_until_complete(client.ping())
        finally:
            loop.run_until_complete(client.close())
        return True
    except Exception as exc:  # pragma: no cover - network failure handled by fallback
        logger.warning(
            "Redis connection test failed for %s: %s",
            _redact_redis_url(redis_url),
            exc,
        )
        return False
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def _redact_redis_url(redis_url: str) -> str:
    if "@" in redis_url:
        return redis_url.split("@", 1)[-1]
    return redis_url


def _parse_int(value: Optional[str], env_key: str) -> Optional[int]:
    if value is None:
        return None
    try:
        parsed = int(value)
        if parsed <= 0:
            logger.warning("%s must be > 0; ignoring value %s", env_key, value)
            return None
        return parsed
    except ValueError:
        logger.warning("%s must be an integer; ignoring value %s", env_key, value)
        return None


def _parse_float(value: Optional[str], env_key: str, *, default: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
        if not 0 < parsed < 1:
            logger.warning("%s must be between 0 and 1; using default %.2f", env_key, default)
            return default
        return parsed
    except ValueError:
        logger.warning("%s must be a float; using default %.2f", env_key, default)
        return default


__all__ = [
    "SessionStorage",
    "InMemorySessionStorage",
    "RedisSessionStorage",
    "create_session_storage",
]
