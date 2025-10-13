"""Tests for OAuth configuration helpers."""

import synapse_mcp.oauth.config as config


def test_should_skip_oauth_with_pat_only():
    assert config.should_skip_oauth({"SYNAPSE_PAT": "token"}) is True


def test_should_not_skip_oauth_when_oauth_credentials_present():
    env = {
        "SYNAPSE_PAT": "token",
        "SYNAPSE_OAUTH_CLIENT_ID": "client",
        "SYNAPSE_OAUTH_CLIENT_SECRET": "secret",
    }
    assert config.should_skip_oauth(env) is False


def test_load_oauth_settings_missing_values():
    assert config.load_oauth_settings({}) is None


def test_load_oauth_settings_normalises_urls():
    env = {
        "SYNAPSE_OAUTH_CLIENT_ID": "client",
        "SYNAPSE_OAUTH_CLIENT_SECRET": "secret",
        "MCP_SERVER_URL": "http://localhost:9000/mcp",
    }

    settings = config.load_oauth_settings(env)
    assert settings is not None
    assert settings.server_url == "http://127.0.0.1:9000"
    assert settings.redirect_uri == "http://127.0.0.1:9000/oauth/callback"
