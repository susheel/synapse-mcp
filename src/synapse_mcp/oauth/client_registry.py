"""Persistence for dynamically registered OAuth clients."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional

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


def create_client_registry(path: Optional[str] = None) -> FileClientRegistry:
    """Create a file-backed registry at the configured path."""

    if path is None:
        path = os.environ.get("SYNAPSE_MCP_CLIENT_REGISTRY_PATH")

    if path is None:
        base_dir = os.environ.get("SYNAPSE_MCP_STATE_DIR")
        if base_dir:
            registry_path = Path(base_dir)
        else:
            registry_path = Path.home() / ".cache" / "synapse-mcp"
        path = str(registry_path / "client_registry.json")

    resolved_path = Path(path).expanduser()
    logger.info("Using client registry path: %s", resolved_path)
    return FileClientRegistry(resolved_path)


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
    "create_client_registry",
    "load_static_registrations",
]
