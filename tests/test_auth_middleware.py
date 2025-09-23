"""Tests for OAuthTokenMiddleware."""

from types import SimpleNamespace

import pytest

from synapse_mcp.auth_middleware import OAuthTokenMiddleware


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


class DummyFastMCPContext:
    def __init__(self):
        self._state = {}
        self.fastmcp = SimpleNamespace(auth=None)
        self.session_id = "session-1"

    def set_state(self, key, value):
        self._state[key] = value

    def get_state(self, key, default=None):
        return self._state.get(key, default)


@pytest.mark.anyio
async def test_middleware_uses_authorization_header():
    middleware = OAuthTokenMiddleware()
    fast_ctx = DummyFastMCPContext()
    message = SimpleNamespace(name="tool", headers={"Authorization": "Bearer tok"})
    context = SimpleNamespace(message=message, fastmcp_context=fast_ctx)

    async def call_next(ctx):
        return "ok"

    result = await middleware.on_call_tool(context, call_next)
    assert result == "ok"
    assert fast_ctx.get_state("oauth_access_token") == "tok"


@pytest.mark.anyio
async def test_middleware_uses_cached_token():
    middleware = OAuthTokenMiddleware()
    fast_ctx = DummyFastMCPContext()
    fast_ctx.set_state("oauth_access_token", "cached-token")
    fast_ctx.set_state("token_scopes", ["view"])
    fast_ctx.set_state("user_subject", "user-1")
    message = SimpleNamespace(name="tool", headers={})
    context = SimpleNamespace(message=message, fastmcp_context=fast_ctx)

    async def call_next(ctx):
        return "ok"

    await middleware.on_call_tool(context, call_next)
    assert fast_ctx.get_state("oauth_access_token") == "cached-token"
    assert fast_ctx.get_state("token_scopes") == ["view"]
    assert fast_ctx.get_state("user_subject") == "user-1"
    assert fast_ctx.get_state("session_id") == "session-1"


@pytest.mark.anyio
async def test_middleware_resolves_token_from_proxy(monkeypatch):
    middleware = OAuthTokenMiddleware()
    fast_ctx = DummyFastMCPContext()

    class FakeProxy:
        async def get_token_for_current_user(self):
            return None

        async def iter_user_tokens(self):
            return [("user-2", "proxy-token")]

    fast_ctx.fastmcp.auth = FakeProxy()
    message = SimpleNamespace(name="tool", headers={})
    context = SimpleNamespace(message=message, fastmcp_context=fast_ctx)

    async def call_next(ctx):
        return "ok"

    await middleware.on_call_resource(context, call_next)
    assert fast_ctx.get_state("oauth_access_token") == "proxy-token"
    assert fast_ctx.get_state("user_subject") == "user-2"


@pytest.mark.anyio
async def test_middleware_picks_first_token_when_multiple(monkeypatch):
    middleware = OAuthTokenMiddleware()
    fast_ctx = DummyFastMCPContext()

    class FakeProxy:
        async def get_token_for_current_user(self):
            return None

        async def iter_user_tokens(self):
            return [("user-2", "token-a"), ("user-3", "token-b")]

    fast_ctx.fastmcp.auth = FakeProxy()
    message = SimpleNamespace(name="tool", headers={})
    context = SimpleNamespace(message=message, fastmcp_context=fast_ctx)

    async def call_next(ctx):
        return "ok"

    await middleware.on_call_tool(context, call_next)
    assert fast_ctx.get_state("oauth_access_token") == "token-a"
    assert fast_ctx.get_state("user_subject") == "user-2"
