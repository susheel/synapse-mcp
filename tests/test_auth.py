"""Tests for OAuth proxy configuration behavior."""

import importlib

import pytest

auth_module = importlib.import_module("synapse_mcp.oauth")


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("SYNAPSE_PAT", raising=False)
    monkeypatch.delenv("SYNAPSE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("SYNAPSE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SYNAPSE_OAUTH_REDIRECT_URI", raising=False)
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)


def test_create_oauth_proxy_skips_when_pat(monkeypatch):
    monkeypatch.setenv("SYNAPSE_PAT", "fake-token")

    assert auth_module.create_oauth_proxy() is None


def test_create_oauth_proxy_returns_none_when_config_missing():
    assert auth_module.create_oauth_proxy() is None


def test_create_oauth_proxy_initializes_session_aware_proxy(monkeypatch):
    monkeypatch.setenv("SYNAPSE_OAUTH_CLIENT_ID", "client")
    monkeypatch.setenv("SYNAPSE_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:9000/mcp")

    captured = {}

    def fake_verifier(*args, **kwargs):
        captured['verifier'] = {'args': args, 'kwargs': kwargs}
        return object()

    def fake_proxy(*args, **kwargs):
        captured['proxy'] = {'args': args, 'kwargs': kwargs}
        return "proxy"

    factory_module = importlib.import_module("synapse_mcp.oauth.factory")

    monkeypatch.setattr(factory_module, "SynapseJWTVerifier", fake_verifier)
    monkeypatch.setattr(factory_module, "SessionAwareOAuthProxy", fake_proxy)

    monkeypatch.setattr(auth_module, "SynapseJWTVerifier", fake_verifier)
    monkeypatch.setattr(auth_module, "SessionAwareOAuthProxy", fake_proxy)

    result = auth_module.create_oauth_proxy()

    assert result == "proxy"

    verifier_call = captured['verifier']
    assert verifier_call['kwargs']['audience'] == "client"

    proxy_call = captured['proxy']
    assert proxy_call['kwargs']['base_url'] == "http://127.0.0.1:9000"
    assert proxy_call['kwargs']['redirect_path'] == "/oauth/callback"
    assert proxy_call['kwargs']['upstream_client_id'] == "client"
    assert proxy_call['kwargs']['upstream_client_secret'] == "secret"
