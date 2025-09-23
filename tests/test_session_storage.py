"""Tests for session storage factory."""

import synapse_mcp.session_storage as storage
from synapse_mcp.session_storage.base import SessionStorage


def test_create_session_storage_defaults_to_memory():
    store = storage.create_session_storage({})
    assert isinstance(store, storage.InMemorySessionStorage)


def test_create_session_storage_prefers_redis(monkeypatch):
    env = {"REDIS_URL": "redis://example"}

    import synapse_mcp.session_storage.redis_backend as redis_backend

    monkeypatch.setattr(redis_backend, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(storage, "REDIS_AVAILABLE", True)

    class DummyStorage(SessionStorage):
        async def set_user_token(self, user_subject: str, access_token: str, ttl_seconds: int = 3600) -> None:
            return None

        async def get_user_token(self, user_subject: str):
            return None

        async def remove_user_token(self, user_subject: str) -> None:
            return None

        async def cleanup_expired_tokens(self) -> None:
            return None

        async def get_all_user_subjects(self):
            return set()

        async def find_user_by_token(self, access_token: str):
            return None

    dummy = DummyStorage()
    monkeypatch.setattr(redis_backend, "RedisSessionStorage", lambda url: dummy)
    monkeypatch.setattr(storage, "RedisSessionStorage", lambda url: dummy)

    store = storage.create_session_storage(env)
    assert store is dummy


def test_create_session_storage_falls_back_when_redis_unavailable(monkeypatch):
    env = {"REDIS_URL": "redis://example"}

    import synapse_mcp.session_storage.redis_backend as redis_backend

    monkeypatch.setattr(redis_backend, "REDIS_AVAILABLE", False)
    monkeypatch.setattr(storage, "REDIS_AVAILABLE", False)

    store = storage.create_session_storage(env)
    assert isinstance(store, storage.InMemorySessionStorage)
