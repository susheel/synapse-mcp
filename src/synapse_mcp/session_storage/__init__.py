"""Session storage factory and exports."""

import logging
import os
from typing import Optional

from .base import SessionStorage
from .memory import InMemorySessionStorage
from .redis_backend import REDIS_AVAILABLE, RedisSessionStorage

logger = logging.getLogger("synapse_mcp.session_storage")


def create_session_storage(env: Optional[dict[str, str]] = None) -> SessionStorage:
    """Create appropriate session storage based on configuration."""
    env = env or os.environ
    redis_url = env.get("REDIS_URL")

    if redis_url and REDIS_AVAILABLE:
        logger.info("Using Redis session storage: %s", _redact_redis_url(redis_url))
        return RedisSessionStorage(redis_url)

    max_tokens = _parse_int(env.get("SYNAPSE_MCP_MEMORY_SESSION_MAX_TOKENS"), "SYNAPSE_MCP_MEMORY_SESSION_MAX_TOKENS")
    warn_fraction = _parse_float(env.get("SYNAPSE_MCP_MEMORY_SESSION_WARN_FRACTION"), "SYNAPSE_MCP_MEMORY_SESSION_WARN_FRACTION", default=0.8)

    if redis_url and not REDIS_AVAILABLE:
        logger.warning("REDIS_URL provided but Redis not available - using in-memory storage")
    else:
        logger.info(
            "No REDIS_URL configured - using in-memory storage (max_tokens=%s warn_fraction=%.2f)",
            max_tokens,
            warn_fraction,
        )

    return InMemorySessionStorage(max_tokens=max_tokens, warn_fraction=warn_fraction)


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
