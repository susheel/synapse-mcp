"""Persistence for dynamically registered OAuth clients."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional

try:
    import redis
    from redis.exceptions import RedisError

    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover - redis optional
    redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[assignment, misc]
    REDIS_AVAILABLE = False

logger = logging.getLogger("synapse_mcp.oauth")


@dataclass
class ClientRegistration:
    """Serializable representation of a dynamically registered client."""

    client_id: str
    client_secret: Optional[str]
    redirect_uris: list[str]
    grant_types: list[str]


class ClientRegistry:
    """Store for registered OAuth clients."""

    def load_all(self) -> Iterable[ClientRegistration]:  # pragma: no cover - interface only
        raise NotImplementedError

    def save(self, registration: ClientRegistration) -> None:  # pragma: no cover - interface only
        raise NotImplementedError

    def remove(self, client_id: str) -> None:  # pragma: no cover - interface only
        raise NotImplementedError


class FileClientRegistry(ClientRegistry):
    """File-backed registry for DCR clients."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> list[ClientRegistration]:
        with self._lock:
            if not self._path.exists():
                return []
            try:
                data = json.loads(self._path.read_text())
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                logger.warning("Failed to parse client registry file %s: %s", self._path, exc)
                return []

        registrations: list[ClientRegistration] = []
        for item in data.values():
            registrations.append(
                ClientRegistration(
                    client_id=item["client_id"],
                    client_secret=item.get("client_secret"),
                    redirect_uris=list(item.get("redirect_uris", [])),
                    grant_types=list(item.get("grant_types", [])),
                )
            )
        return registrations

    def save(self, registration: ClientRegistration) -> None:
        with self._lock:
            records = {}
            if self._path.exists():
                try:
                    records = json.loads(self._path.read_text())
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    logger.warning("Resetting corrupt client registry file %s: %s", self._path, exc)
            records[registration.client_id] = asdict(registration)
            self._path.write_text(json.dumps(records, indent=2))

    def remove(self, client_id: str) -> None:
        with self._lock:
            if not self._path.exists():
                return
            try:
                records = json.loads(self._path.read_text())
            except json.JSONDecodeError:  # pragma: no cover - defensive
                return
            if client_id in records:
                records.pop(client_id, None)
                self._path.write_text(json.dumps(records, indent=2))


class RedisClientRegistry(ClientRegistry):
    """Redis-backed registry for DCR clients."""

    def __init__(self, redis_url: str, namespace: str = "synapse_mcp:client_registry") -> None:
        if not REDIS_AVAILABLE:  # pragma: no cover - defensive
            raise RuntimeError("Redis support not available - install redis package")
        self._namespace = namespace
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def load_all(self) -> list[ClientRegistration]:
        try:
            records = self._redis.hgetall(self._namespace)
        except RedisError as exc:  # pragma: no cover - network failures
            logger.warning("Failed to load client registry from Redis: %s", exc)
            return []

        registrations: list[ClientRegistration] = []
        for raw in records.values():
            try:
                item = json.loads(raw)
                registrations.append(
                    ClientRegistration(
                        client_id=item["client_id"],
                        client_secret=item.get("client_secret"),
                        redirect_uris=list(item.get("redirect_uris", [])),
                        grant_types=list(item.get("grant_types", [])),
                    )
                )
            except (KeyError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
                logger.warning("Skipping malformed Redis client record: %s", exc)
        return registrations

    def save(self, registration: ClientRegistration) -> None:
        try:
            self._redis.hset(self._namespace, registration.client_id, json.dumps(asdict(registration)))
        except RedisError as exc:  # pragma: no cover - network failures
            logger.warning("Failed to persist client %s to Redis: %s", registration.client_id, exc)

    def remove(self, client_id: str) -> None:
        try:
            self._redis.hdel(self._namespace, client_id)
        except RedisError as exc:  # pragma: no cover - network failures
            logger.warning("Failed to remove client %s from Redis: %s", client_id, exc)


def create_client_registry(env: Optional[dict[str, str]] = None, path: Optional[str] = None) -> ClientRegistry:
    """Create a registry backend based on configuration."""

    env = env or os.environ
    backend = (env.get("SYNAPSE_MCP_CLIENT_REGISTRY_BACKEND") or "auto").lower()

    if backend == "auto":
        backend = "redis" if env.get("REDIS_URL") else "file"

    if backend == "redis":
        redis_url = env.get("SYNAPSE_MCP_CLIENT_REGISTRY_REDIS_URL") or env.get("REDIS_URL")
        if redis_url and REDIS_AVAILABLE:
            logger.info("Using Redis client registry at %s", _redact_redis_url(redis_url))
            return RedisClientRegistry(redis_url)
        logger.warning("Redis client registry requested but unavailable; falling back to file backend")

    if path is None:
        path = env.get("SYNAPSE_MCP_CLIENT_REGISTRY_PATH")

    if path is None:
        base_dir = env.get("SYNAPSE_MCP_STATE_DIR")
        if base_dir:
            registry_path = Path(base_dir)
        else:
            registry_path = Path.home() / ".cache" / "synapse-mcp"
        path = str(registry_path / "client_registry.json")

    resolved_path = Path(path).expanduser()
    logger.info("Using file client registry path: %s", resolved_path)
    return FileClientRegistry(resolved_path)


def _redact_redis_url(redis_url: str) -> str:
    if "@" in redis_url:
        return redis_url.split("@", 1)[-1]
    return redis_url


def load_static_registrations() -> list[ClientRegistration]:
    """Load statically configured clients from environment or file."""

    raw = os.environ.get("SYNAPSE_MCP_STATIC_CLIENTS")
    path = os.environ.get("SYNAPSE_MCP_STATIC_CLIENTS_PATH")

    data: Optional[str] = None
    if path:
        try:
            data = Path(path).expanduser().read_text()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to read static client file %s: %s", path, exc)
    elif raw:
        data = raw

    if not data:
        return []

    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        logger.warning("Invalid JSON in static client configuration: %s", exc)
        return []

    registrations: list[ClientRegistration] = []
    if not isinstance(payload, list):
        logger.warning("Static client configuration must be a list of objects")
        return []

    for item in payload:
        try:
            registrations.append(
                ClientRegistration(
                    client_id=item["client_id"],
                    client_secret=item.get("client_secret"),
                    redirect_uris=list(item.get("redirect_uris", [])),
                    grant_types=list(item.get("grant_types", [])),
                )
            )
        except KeyError as exc:  # pragma: no cover - defensive
            logger.warning("Skipping malformed static client entry missing %s", exc)
    return registrations


__all__ = [
    "ClientRegistration",
    "ClientRegistry",
    "FileClientRegistry",
    "RedisClientRegistry",
    "create_client_registry",
    "load_static_registrations",
]
