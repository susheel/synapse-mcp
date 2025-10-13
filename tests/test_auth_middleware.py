"""Tests for MCP-compliant OAuthTokenMiddleware."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
import pytest

from synapse_mcp.auth_middleware import (
    AuthenticationError,
    OAuthTokenMiddleware,
    validate_jwt_token,
)


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def create_valid_jwt(expires_in_seconds=3600, include_exp=True, **extra_claims):
    """Create a valid JWT token for testing."""
    payload = {
        "sub": "user-123",
        "iat": datetime.now(timezone.utc).timestamp(),
    }

    if include_exp:
        payload["exp"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).timestamp()

    payload.update(extra_claims)

    # Encode without signature (for testing)
    return jwt.encode(payload, "secret", algorithm="HS256")


def create_expired_jwt():
    """Create an expired JWT token for testing."""
    return create_valid_jwt(expires_in_seconds=-3600)  # Expired 1 hour ago


class DummyFastMCPContext:
    def __init__(self):
        self._state = {}
        self.fastmcp = SimpleNamespace(auth=None)
        self.session_id = "session-1"

    def set_state(self, key, value):
        self._state[key] = value

    def get_state(self, key, default=None):
        return self._state.get(key, default)


class DummyHTTPRequest:
    """Mock HTTP request for testing."""
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.url = "http://test.com/mcp"
        self.method = "POST"


# ============================================================================
# Token Validation Tests
# ============================================================================


def test_validate_jwt_token_valid():
    """Valid token with expiration should pass validation."""
    token = create_valid_jwt(expires_in_seconds=3600)
    # Should not raise
    validate_jwt_token(token)


def test_validate_jwt_token_expired():
    """Expired token should raise AuthenticationError."""
    token = create_expired_jwt()
    with pytest.raises(AuthenticationError) as exc_info:
        validate_jwt_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in str(exc_info.value.detail).lower()


def test_validate_jwt_token_missing_exp():
    """Token without expiration claim should raise AuthenticationError."""
    token = create_valid_jwt(include_exp=False)
    with pytest.raises(AuthenticationError) as exc_info:
        validate_jwt_token(token)
    assert exc_info.value.status_code == 401
    assert "expiration" in str(exc_info.value.detail).lower()


def test_validate_jwt_token_invalid_format():
    """Malformed JWT should raise AuthenticationError."""
    invalid_token = "not.a.valid.jwt.token"
    with pytest.raises(AuthenticationError) as exc_info:
        validate_jwt_token(invalid_token)
    assert exc_info.value.status_code == 401


# ============================================================================
# Middleware Integration Tests
# ============================================================================


@pytest.mark.anyio
async def test_middleware_extracts_valid_token_from_authorization_header():
    """Valid token in Authorization header should be extracted and validated."""
    token = create_valid_jwt()

    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = DummyHTTPRequest(
            headers={"authorization": f"Bearer {token}"}
        )

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        context = SimpleNamespace(fastmcp_context=fast_ctx)

        async def call_next(ctx):
            return "ok"

        result = await middleware.on_call_tool(context, call_next)
        assert result == "ok"
        assert fast_ctx.get_state("oauth_access_token") == token


@pytest.mark.anyio
async def test_middleware_rejects_missing_authorization_header():
    """Missing Authorization header should raise HTTP 401."""
    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = DummyHTTPRequest(headers={})

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        context = SimpleNamespace(fastmcp_context=fast_ctx)

        async def call_next(ctx):
            return "ok"

        with pytest.raises(AuthenticationError) as exc_info:
            await middleware.on_call_tool(context, call_next)

        assert exc_info.value.status_code == 401
        assert "Authorization" in exc_info.value.detail


@pytest.mark.anyio
async def test_middleware_rejects_expired_token():
    """Expired token should raise HTTP 401."""
    expired_token = create_expired_jwt()

    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = DummyHTTPRequest(
            headers={"authorization": f"Bearer {expired_token}"}
        )

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        context = SimpleNamespace(fastmcp_context=fast_ctx)

        async def call_next(ctx):
            return "ok"

        with pytest.raises(AuthenticationError) as exc_info:
            await middleware.on_call_tool(context, call_next)

        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()


@pytest.mark.anyio
async def test_middleware_rejects_malformed_token():
    """Malformed JWT should raise HTTP 401."""
    malformed_token = "not.a.valid.jwt"

    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = DummyHTTPRequest(
            headers={"authorization": f"Bearer {malformed_token}"}
        )

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        context = SimpleNamespace(fastmcp_context=fast_ctx)

        async def call_next(ctx):
            return "ok"

        with pytest.raises(AuthenticationError) as exc_info:
            await middleware.on_call_tool(context, call_next)

        assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_middleware_extracts_token_from_context_headers():
    """Token in context message headers should work as fallback."""
    token = create_valid_jwt()

    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = None  # No HTTP request available

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        message = SimpleNamespace(name="tool", headers={"Authorization": f"Bearer {token}"})
        context = SimpleNamespace(message=message, fastmcp_context=fast_ctx)

        async def call_next(ctx):
            return "ok"

        result = await middleware.on_call_tool(context, call_next)
        assert result == "ok"
        assert fast_ctx.get_state("oauth_access_token") == token


@pytest.mark.anyio
async def test_middleware_extracts_token_from_auth_context():
    """Token in auth_context should work as fallback."""
    token = create_valid_jwt()

    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = None  # No HTTP request available

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        auth_context = SimpleNamespace(token=token, subject="user-123")
        context = SimpleNamespace(
            auth_context=auth_context,
            message=SimpleNamespace(headers={}),
            fastmcp_context=fast_ctx
        )

        async def call_next(ctx):
            return "ok"

        result = await middleware.on_call_tool(context, call_next)
        assert result == "ok"
        assert fast_ctx.get_state("oauth_access_token") == token


@pytest.mark.anyio
async def test_middleware_works_for_resource_calls():
    """Middleware should validate tokens for resource calls too."""
    token = create_valid_jwt()

    with patch("synapse_mcp.auth_middleware.get_http_request") as mock_get_request:
        mock_get_request.return_value = DummyHTTPRequest(
            headers={"authorization": f"Bearer {token}"}
        )

        middleware = OAuthTokenMiddleware()
        fast_ctx = DummyFastMCPContext()
        context = SimpleNamespace(fastmcp_context=fast_ctx)

        async def call_next(ctx):
            return "ok"

        result = await middleware.on_call_resource(context, call_next)
        assert result == "ok"
        assert fast_ctx.get_state("oauth_access_token") == token
