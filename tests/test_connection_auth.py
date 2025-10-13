"""Tests for connection_auth module.

Tests that connection_auth correctly reads OAuth tokens from context
that were set by the auth_middleware.
"""

from types import SimpleNamespace

import pytest

import synapse_mcp.connection_auth as connection_auth


class DummyContext:
    def __init__(self, oauth_token=None):
        self._state = {}
        self.session_id = "session-1"
        # Middleware would have set the oauth_access_token in context
        if oauth_token:
            self._state["oauth_access_token"] = oauth_token

    def get_state(self, key):
        if key in self._state:
            return self._state[key]
        raise KeyError

    def set_state(self, key, value):
        self._state[key] = value


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


def test_oauth_authentication_uses_token_from_context(patched_synapse):
    """Test that connection_auth reads OAuth token from context (set by middleware)."""
    # Middleware has already set the token in context
    ctx = DummyContext(oauth_token="token-abc")

    client = connection_auth.get_synapse_client(ctx)
    assert patched_synapse[0].logged_in == "token-abc"
    assert connection_auth._get_state(ctx, connection_auth.SYNAPSE_CLIENT_KEY) is client
    assert connection_auth._get_state(ctx, "oauth_access_token") == "token-abc"
