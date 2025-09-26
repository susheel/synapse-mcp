"""Tests for client registry backends."""

import json
from dataclasses import asdict

import pytest

pytest.importorskip("redis")

from synapse_mcp.oauth.client_registry import (
    ClientRegistration,
    FileClientRegistry,
    RedisClientRegistry,
    create_client_registry,
)


class FakeRedis:
    def __init__(self):
        self.data: dict[str, dict[str, str]] = {}

    def hgetall(self, key: str):
        return self.data.get(key, {}).copy()

    def hset(self, key: str, field: str, value: str):
        self.data.setdefault(key, {})[field] = value

    def hdel(self, key: str, field: str):
        if key in self.data:
            self.data[key].pop(field, None)


@pytest.fixture
def fake_redis(monkeypatch):
    instance = FakeRedis()

    def _from_url(url: str, decode_responses: bool = False):  # noqa: D401 - matches redis signature
        return instance

    monkeypatch.setattr("synapse_mcp.oauth.client_registry.redis.Redis.from_url", _from_url)
    return instance


def make_registration(idx: int) -> ClientRegistration:
    return ClientRegistration(
        client_id=f"client-{idx}",
        client_secret=None,
        redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
        grant_types=["authorization_code"],
    )


def test_redis_registry_round_trip(fake_redis):
    env = {
        "SYNAPSE_MCP_CLIENT_REGISTRY_BACKEND": "redis",
        "SYNAPSE_MCP_CLIENT_REGISTRY_REDIS_URL": "redis://localhost/0",
    }

    registry = create_client_registry(env)
    assert isinstance(registry, RedisClientRegistry)

    registration = make_registration(1)
    registry.save(registration)

    loaded = registry.load_all()
    assert len(loaded) == 1
    assert loaded[0] == registration

    registry.remove(registration.client_id)
    assert registry.load_all() == []


def test_create_registry_prefers_redis_when_auto(fake_redis):
    env = {"REDIS_URL": "redis://example/0"}
    registry = create_client_registry(env)
    assert isinstance(registry, RedisClientRegistry)


def test_file_registry_resolves_path(tmp_path, monkeypatch):
    path = tmp_path / "client_registry.json"
    env = {
        "SYNAPSE_MCP_CLIENT_REGISTRY_BACKEND": "file",
        "SYNAPSE_MCP_CLIENT_REGISTRY_PATH": str(path),
    }

    registry = create_client_registry(env)
    assert isinstance(registry, FileClientRegistry)

    registration = make_registration(2)
    registry.save(registration)

    contents = json.loads(path.read_text())
    assert registration.client_id in contents
    assert contents[registration.client_id] == asdict(registration)
