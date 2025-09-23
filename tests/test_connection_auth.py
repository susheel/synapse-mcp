"""Tests for connection_auth fallbacks."""

from types import SimpleNamespace

import pytest

import synapse_mcp.connection_auth as connection_auth


class DummyContext:
    def __init__(self, proxy):
        self._state = {}
        self.session_id = "session-1"
        self.fastmcp_context = SimpleNamespace(
            session_id="session-1",
            fastmcp=SimpleNamespace(auth=proxy),
        )

    def get_state(self, key):
        if key in self._state:
            return self._state[key]
        raise KeyError

    def set_state(self, key, value):
        self._state[key] = value


@pytest.fixture
def dummy_proxy():
    class Proxy:
        def __init__(self):
            self.mapping = {"session-1": ("token-abc", "user-123")}

        def get_session_token_info(self, session_id):
            return self.mapping.get(session_id)

    return Proxy()


@pytest.fixture
def patched_synapse(monkeypatch):
    created = []

    class DummySynapse:
        def __init__(self, *args, **kwargs):
            self.init_args = args
            self.init_kwargs = kwargs
            self.logged_in = None
            created.append(self)

        def login(self, authToken=None, **kwargs):
            self.logged_in = authToken

        def getUserProfile(self):
            return {"ownerId": "user-123", "userName": "tester"}

    monkeypatch.setattr(connection_auth.synapseclient, "Synapse", DummySynapse)
    return created


def test_oauth_fallback_uses_session_mapping(dummy_proxy, patched_synapse):
    ctx = DummyContext(dummy_proxy)

    client = connection_auth.get_synapse_client(ctx)
    assert patched_synapse[0].logged_in == "token-abc"
    assert connection_auth._get_state(ctx, connection_auth.SYNAPSE_CLIENT_KEY) is client
    assert connection_auth._get_state(ctx, "oauth_access_token") == "token-abc"
