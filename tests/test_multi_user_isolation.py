"""Connection-scoped authentication regression tests."""

import pytest

import synapse_mcp
import synapse_mcp.connection_auth as connection_auth
from synapse_mcp.connection_auth import ConnectionAuthError, get_user_auth_info


class DummyContext:
    def __init__(self):
        self._state = {}

    def get_state(self, key, default=None):
        return self._state.get(key, default)

    def set_state(self, key, value):
        self._state[key] = value


def _make_client(user_id: str):
    class _Client:
        def __init__(self, user):
            self._user = user

        def login(self, **kwargs):
            return None

        def getUserProfile(self):
            return {
                "ownerId": self._user,
                "userName": f"{self._user}@example.com",
            }

    return _Client(user_id)


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("SYNAPSE_PAT", raising=False)


def test_get_synapse_client_creates_connection_scoped_clients(monkeypatch):
    ctx1 = DummyContext()
    ctx2 = DummyContext()

    clients = [_make_client("user1"), _make_client("user2")]
    monkeypatch.setattr(connection_auth.synapseclient, "Synapse", lambda *args, **kwargs: clients.pop(0))
    monkeypatch.setenv("SYNAPSE_PAT", "fake-pat")

    client1 = connection_auth.get_synapse_client(ctx1)
    client2 = connection_auth.get_synapse_client(ctx2)

    assert client1 is not client2
    assert get_user_auth_info(ctx1)["user_id"] == "user1"
    assert get_user_auth_info(ctx2)["user_id"] == "user2"


def test_get_synapse_client_uses_cached_client(monkeypatch):
    ctx = DummyContext()
    created = []

    def factory(*args, **kwargs):
        client = _make_client("cached")
        created.append(client)
        return client

    monkeypatch.setattr(connection_auth.synapseclient, "Synapse", factory)
    monkeypatch.setenv("SYNAPSE_PAT", "fake-pat")

    first = connection_auth.get_synapse_client(ctx)
    second = connection_auth.get_synapse_client(ctx)

    assert first is second
    assert len(created) == 1


def test_get_synapse_client_requires_credentials(monkeypatch):
    ctx = DummyContext()

    monkeypatch.setattr(connection_auth.synapseclient, "Synapse", lambda *args, **kwargs: _make_client("anon"))

    with pytest.raises(ConnectionAuthError):
        connection_auth.get_synapse_client(ctx)


def test_get_entity_operations_are_per_connection(monkeypatch):
    ctx1 = DummyContext()
    ctx2 = DummyContext()

    client1 = _make_client("user1")
    client2 = _make_client("user2")

    import synapse_mcp.context_helpers as context_helpers

    monkeypatch.setattr(context_helpers, "get_synapse_client", lambda ctx: client1 if ctx is ctx1 else client2)

    ops1 = synapse_mcp.get_entity_operations(ctx1)
    ops2 = synapse_mcp.get_entity_operations(ctx2)

    assert ops1 is not ops2
    assert ops1["base"].synapse_client is client1
    assert ops2["base"].synapse_client is client2


def test_deprecated_globals_return_safe_defaults():
    assert synapse_mcp.initialize_authentication() == (False, False)
    assert synapse_mcp.authenticate_synapse_client("token") is False
    assert synapse_mcp.is_authenticated() is False
    assert synapse_mcp.is_using_pat_auth() is False
