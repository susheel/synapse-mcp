"""Tests for the session-aware OAuth proxy."""

from types import SimpleNamespace
import sys

import pytest

from fastmcp.server.auth.oauth_proxy import OAuthProxy

from synapse_mcp.oauth.proxy import SessionAwareOAuthProxy


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeStorage:
    def __init__(self):
        self.tokens = {}
        self.set_calls = []
        self.removed = []

    async def get_all_user_subjects(self):
        return set(self.tokens.keys())

    async def find_user_by_token(self, token):
        for subject, stored in self.tokens.items():
            if stored == token:
                return subject
        return None

    async def set_user_token(self, user_subject, access_token, ttl_seconds=3600):
        self.tokens[user_subject] = access_token
        self.set_calls.append((user_subject, access_token))

    async def get_user_token(self, user_subject):
        return self.tokens.get(user_subject)

    async def remove_user_token(self, user_subject):
        self.tokens.pop(user_subject, None)
        self.removed.append(user_subject)

    async def cleanup_expired_tokens(self):
        return None


def build_proxy(monkeypatch, storage):
    monkeypatch.setattr("synapse_mcp.oauth.proxy.create_session_storage", lambda: storage)
    return SessionAwareOAuthProxy(
        upstream_authorization_endpoint="https://auth",
        upstream_token_endpoint="https://token",
        upstream_client_id="client",
        upstream_client_secret="secret",
        redirect_path="/oauth/callback",
        token_verifier=SimpleNamespace(required_scopes=[]),
        base_url="http://localhost",
    )


@pytest.mark.anyio
async def test_map_new_tokens_populates_storage(monkeypatch):
    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage)
    proxy._access_tokens = {"token123": object()}

    dummy_jwt = SimpleNamespace(decode=lambda token, options=None: {"sub": "user-1"})
    monkeypatch.setitem(sys.modules, "jwt", dummy_jwt)

    await proxy._map_new_tokens_to_users()

    assert storage.tokens["user-1"] == "token123"


@pytest.mark.anyio
async def test_get_token_for_current_user(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-1"] = "token123"
    proxy = build_proxy(monkeypatch, storage)

    result = await proxy.get_token_for_current_user()
    assert result == ("token123", "user-1")
    assert await proxy.iter_user_tokens() == [("user-1", "token123")]


@pytest.mark.anyio
async def test_get_token_for_session(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-1"] = "token123"
    proxy = build_proxy(monkeypatch, storage)
    proxy._session_tokens["session-1"] = ("token123", "user-1")

    result = await proxy.get_token_for_session("session-1")
    assert result == ("token123", "user-1")


@pytest.mark.anyio
async def test_cleanup_expired_tokens_removes_orphans(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-1"] = "token123"
    proxy = build_proxy(monkeypatch, storage)

    proxy._access_tokens = {"token123": object(), "token999": object()}
    monkeypatch.setattr(SessionAwareOAuthProxy, "_is_token_old_enough_to_cleanup", lambda self, token: True)

    await proxy.cleanup_expired_tokens()

    assert "token999" not in proxy._access_tokens
    assert "token123" in proxy._access_tokens


@pytest.mark.anyio
async def test_handle_callback_tracks_new_codes(monkeypatch):
    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage)
    proxy._client_codes["existing"] = {"idp_tokens": {}}

    async def fake_handle(self, request, *args, **kwargs):
        # Simulate upstream proxy creating a new authorization code entry
        self._client_codes["fresh-code"] = {"idp_tokens": {}}
        return "ok"

    monkeypatch.setattr(OAuthProxy, "_handle_idp_callback", fake_handle)

    request = SimpleNamespace(headers={"mcp-session-id": "session-123"})

    result = await proxy._handle_idp_callback(request)

    assert result == "ok"
    assert proxy._code_sessions["fresh-code"] == "session-123"
    # Existing codes should not be remapped to the new session
    assert "existing" not in proxy._code_sessions


@pytest.mark.anyio
async def test_exchange_binds_session_and_storage(monkeypatch):
    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage)
    proxy._code_sessions["code-1"] = "session-xyz"

    dummy_jwt = SimpleNamespace(decode=lambda token, options=None: {"sub": "user-1"})
    monkeypatch.setitem(sys.modules, "jwt", dummy_jwt)

    async def fake_exchange(self, client, authorization_code):
        self._access_tokens["tokenXYZ"] = SimpleNamespace(
            client_id=client.client_id, scopes=list(authorization_code.scopes), expires_at=0
        )
        return SimpleNamespace(access_token="tokenXYZ")

    monkeypatch.setattr(OAuthProxy, "exchange_authorization_code", fake_exchange)

    client = SimpleNamespace(client_id="client-1")
    authorization_code = SimpleNamespace(code="code-1", scopes=["view"])

    result = await proxy.exchange_authorization_code(client, authorization_code)

    assert result.access_token == "tokenXYZ"
    assert proxy._code_sessions == {}
    assert proxy._session_tokens["session-xyz"] == ("tokenXYZ", "user-1")
    assert storage.tokens["user-1"] == "tokenXYZ"


@pytest.mark.anyio
async def test_exchange_fallback_uses_existing_token(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-99"] = "tokenABC"
    proxy = build_proxy(monkeypatch, storage)
    proxy._code_sessions["code-2"] = "session-abc"
    proxy._access_tokens["tokenABC"] = SimpleNamespace(client_id="client-77", scopes=["download"], expires_at=0)

    async def fake_exchange(self, client, authorization_code):
        # Simulate upstream not rotating tokens (no new entries added)
        return SimpleNamespace(access_token="tokenABC")

    monkeypatch.setattr(OAuthProxy, "exchange_authorization_code", fake_exchange)

    client = SimpleNamespace(client_id="client-77")
    authorization_code = SimpleNamespace(code="code-2", scopes=["download"])

    result = await proxy.exchange_authorization_code(client, authorization_code)

    assert result.access_token == "tokenABC"
    assert proxy._code_sessions == {}
    assert proxy._session_tokens["session-abc"] == ("tokenABC", "user-99")
