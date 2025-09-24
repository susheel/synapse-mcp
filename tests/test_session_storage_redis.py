"""Tests for Redis-backed session storage semantics."""

from collections import defaultdict
from types import SimpleNamespace

import pytest

import synapse_mcp.session_storage.redis_backend as redis_backend
from synapse_mcp.session_storage.redis_backend import RedisSessionStorage


pytestmark = pytest.mark.anyio("asyncio")


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}
        self._sets: dict[str, set[str]] = defaultdict(set)
        self._now = 0.0
        self.closed = False

    def advance(self, seconds: float) -> None:
        self._now += seconds

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = (value, self._now + float(ttl))

    async def get(self, key: str):
        self._purge_if_expired(key)
        entry = self._store.get(key)
        return entry[0] if entry else None

    async def exists(self, key: str):
        self._purge_if_expired(key)
        return 1 if key in self._store else 0

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def sadd(self, key: str, *values: str):
        self._sets[key].update(values)

    async def srem(self, key: str, *values: str):
        removed = 0
        for value in values:
            if value in self._sets.get(key, set()):
                self._sets[key].remove(value)
                removed += 1
        if key in self._sets and not self._sets[key]:
            self._sets.pop(key, None)
        return removed

    async def smembers(self, key: str):
        return set(self._sets.get(key, set()))

    async def sscan(self, key: str, cursor: int, count: int = 10):
        members = list(self._sets.get(key, set()))
        cursor_index = int(cursor)
        if not members:
            return 0, []
        if cursor_index >= len(members):
            cursor_index = 0
        start = cursor_index
        end = min(start + count, len(members))
        next_cursor = 0 if end >= len(members) else end
        batch = members[start:end]
        return next_cursor, batch

    async def ping(self):
        return True

    async def close(self):
        self.closed = True

    def from_url(self, *_args, **_kwargs):
        return self

    def pipeline(self):
        return FakePipeline(self)

    def _purge_if_expired(self, key: str) -> None:
        entry = self._store.get(key)
        if not entry:
            return
        value, expiry = entry
        if expiry <= self._now:
            self._store.pop(key, None)


class FakePipeline:
    def __init__(self, redis_client: FakeRedis) -> None:
        self._redis = redis_client
        self._commands: list[tuple[str, tuple]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._commands.clear()

    def setex(self, key: str, ttl: int, value: str):
        self._commands.append(("setex", (key, ttl, value)))

    def sadd(self, key: str, value: str):
        self._commands.append(("sadd", (key, value)))

    def delete(self, key: str):
        self._commands.append(("delete", (key,)))

    def srem(self, key: str, value: str):
        self._commands.append(("srem", (key, value)))

    def exists(self, key: str):
        self._commands.append(("exists", (key,)))

    async def execute(self):
        results: list[int] = []
        for command, key in self._commands:
            if command == "setex":
                await self._redis.setex(*key)
            elif command == "sadd":
                await self._redis.sadd(*key)
            elif command == "delete":
                await self._redis.delete(*key)
            elif command == "srem":
                await self._redis.srem(*key)
            elif command == "exists":
                exists = await self._redis.exists(*key)
                results.append(bool(exists))
        self._commands.clear()
        return results


@pytest.fixture
def fake_redis(monkeypatch) -> FakeRedis:
    fake = FakeRedis()
    redis_backend.REDIS_AVAILABLE = True
    monkeypatch.setattr(redis_backend, "redis", SimpleNamespace(from_url=fake.from_url))
    return fake


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_expired_tokens_are_not_returned(fake_redis: FakeRedis):
    storage = RedisSessionStorage("redis://fake")

    await storage.set_user_token("user-1", "token-1", ttl_seconds=5)
    assert await storage.get_user_token("user-1") == "token-1"

    fake_redis.advance(10)

    assert await storage.get_user_token("user-1") is None
    assert await storage.find_user_by_token("token-1") is None
    assert await storage.get_all_user_subjects() == set()


@pytest.mark.anyio
async def test_setting_new_token_replaces_old_indices(fake_redis: FakeRedis):
    storage = RedisSessionStorage("redis://fake")

    await storage.set_user_token("user-1", "token-old", ttl_seconds=100)
    await storage.set_user_token("user-1", "token-new", ttl_seconds=100)

    assert await storage.get_user_token("user-1") == "token-new"
    assert await storage.find_user_by_token("token-new") == "user-1"
    assert await storage.find_user_by_token("token-old") is None

    await storage.remove_user_token("user-1")
    assert await storage.get_user_token("user-1") is None
    assert await storage.find_user_by_token("token-new") is None
