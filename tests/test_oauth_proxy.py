"""Tests for the session-aware OAuth proxy."""

import json
from types import SimpleNamespace
import sys

import pytest
from fastmcp.server.auth.oauth_proxy import OAuthClientInformationFull, OAuthProxy
from starlette.responses import RedirectResponse

from synapse_mcp.oauth.proxy import SessionAwareOAuthProxy


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeRegistry:
    def __init__(self):
        self.records = {}

    def load_all(self):
        return list(self.records.values())

    def save(self, registration):
        self.records[registration.client_id] = registration

    def remove(self, client_id):
        self.records.pop(client_id, None)


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


def build_proxy(monkeypatch, storage, registry: FakeRegistry | None = None):
    monkeypatch.setattr("synapse_mcp.oauth.proxy.create_session_storage", lambda: storage)
    if registry is not None:
        monkeypatch.setattr("synapse_mcp.oauth.proxy.create_client_registry", lambda *_, **__: registry)
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
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())
    proxy._access_tokens = {"token123": object()}

    dummy_jwt = SimpleNamespace(decode=lambda token, options=None: {"sub": "user-1"})
    monkeypatch.setitem(sys.modules, "jwt", dummy_jwt)

    await proxy._map_new_tokens_to_users()

    assert storage.tokens["user-1"] == "token123"


@pytest.mark.anyio
async def test_get_token_for_current_user(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-1"] = "token123"
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())

    result = await proxy.get_token_for_current_user()
    assert result == ("token123", "user-1")
    assert await proxy.iter_user_tokens() == [("user-1", "token123")]


@pytest.mark.anyio
async def test_get_token_for_session(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-1"] = "token123"
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())
    proxy._session_tokens["session-1"] = ("token123", "user-1")

    result = await proxy.get_token_for_session("session-1")
    assert result == ("token123", "user-1")


@pytest.mark.anyio
async def test_cleanup_expired_tokens_removes_orphans(monkeypatch):
    storage = FakeStorage()
    storage.tokens["user-1"] = "token123"
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())

    proxy._access_tokens = {"token123": object(), "token999": object()}
    monkeypatch.setattr(SessionAwareOAuthProxy, "_is_token_old_enough_to_cleanup", lambda self, token: True)

    await proxy.cleanup_expired_tokens()

    assert "token999" not in proxy._access_tokens
    assert "token123" in proxy._access_tokens


@pytest.mark.anyio
async def test_handle_callback_tracks_new_codes(monkeypatch):
    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())
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
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())
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
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())
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


@pytest.mark.anyio
async def test_handle_callback_sanitizes_none_state(monkeypatch):
    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())

    async def fake_handle(self, request, *args, **kwargs):
        return RedirectResponse("http://app/callback?code=new-token&state=None")

    monkeypatch.setattr(OAuthProxy, "_handle_idp_callback", fake_handle)

    request = SimpleNamespace(headers={"mcp-session-id": "session-1"})

    response = await proxy._handle_idp_callback(request)

    assert isinstance(response, RedirectResponse)
    location = response.headers["location"]
    assert "code=new-token" in location
    assert "state=None" not in location
    assert "state=" not in location


@pytest.mark.anyio
async def test_handle_callback_preserves_valid_state(monkeypatch):
    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())

    async def fake_handle(self, request, *args, **kwargs):
        return RedirectResponse("http://app/callback?code=token&state=valid123")

    monkeypatch.setattr(OAuthProxy, "_handle_idp_callback", fake_handle)

    request = SimpleNamespace(headers={"mcp-session-id": "session-2"})

    response = await proxy._handle_idp_callback(request)

    assert response.headers["location"].endswith("state=valid123")

@pytest.mark.anyio
async def test_client_registry_persists_across_instances(monkeypatch, tmp_path):
    registry_path = tmp_path / "clients.json"
    monkeypatch.setenv("SYNAPSE_MCP_CLIENT_REGISTRY_PATH", str(registry_path))

    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage)

    client_info = OAuthClientInformationFull(
        client_id="client-xyz",
        client_secret="secret",
        redirect_uris=["http://127.0.0.1:5000/callback"],
        grant_types=["authorization_code"],
    )

    await proxy.register_client(client_info)

    saved = json.loads(registry_path.read_text())
    assert "client-xyz" in saved

    new_storage = FakeStorage()
    new_proxy = build_proxy(monkeypatch, new_storage)

    assert "client-xyz" in new_proxy._clients


@pytest.mark.anyio
async def test_static_clients_loaded_from_env(monkeypatch):
    payload = json.dumps(
        [
            {
                "client_id": "static-client",
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
            }
        ]
    )
    monkeypatch.setenv("SYNAPSE_MCP_STATIC_CLIENTS", payload)

    storage = FakeStorage()
    proxy = build_proxy(monkeypatch, storage, FakeRegistry())

    assert "static-client" in proxy._clients
