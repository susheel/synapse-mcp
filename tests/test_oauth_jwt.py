"""Tests for Synapse JWT verifier."""

import asyncio
from types import SimpleNamespace

import pytest

import synapse_mcp.oauth.jwt as jwt_module


def _setup_jwt_mocks(monkeypatch, decoded_payload):
    class DummyKey:
        key = "secret"
        algorithm_name = "RS256"

    def fake_get_signing_key(self, token):
        return DummyKey()

    monkeypatch.setattr(jwt_module.PyJWKClient, "get_signing_key_from_jwt", fake_get_signing_key)
    monkeypatch.setattr(jwt_module, "decode", lambda **kwargs: decoded_payload)


def test_verify_token_success(monkeypatch):
    decoded = {
        "sub": "user",
        "aud": "client",
        "exp": 123,
        "access": {"scope": ["view", "download", "modify"]},
    }
    _setup_jwt_mocks(monkeypatch, decoded)

    verifier = jwt_module.SynapseJWTVerifier(
        jwks_uri="http://example/jwks",
        issuer="issuer",
        audience="client",
        required_scopes=["view", "download"],
    )

    result: SimpleNamespace = verifier._verify_token_sync("token")  # type: ignore[attr-defined]
    assert result.sub == "user"
    assert result.scopes == ["view", "download", "modify"]


def test_verify_token_missing_scope_returns_none(monkeypatch):
    decoded = {
        "sub": "user",
        "aud": "client",
        "exp": 123,
        "access": {"scope": ["view"]},
    }
    _setup_jwt_mocks(monkeypatch, decoded)

    verifier = jwt_module.SynapseJWTVerifier(
        jwks_uri="http://example/jwks",
        issuer="issuer",
        audience="client",
        required_scopes=["view", "download"],
    )

    result = verifier._verify_token_sync("token")  # type: ignore[attr-defined]
    assert result is None


def test_verify_token_handles_decode_error(monkeypatch):
    def raise_error(**kwargs):
        raise jwt_module.PyJWTError("boom")

    class DummyKey:
        key = "secret"
        algorithm_name = "RS256"

    monkeypatch.setattr(jwt_module.PyJWKClient, "get_signing_key_from_jwt", lambda self, token: DummyKey())
    monkeypatch.setattr(jwt_module, "decode", raise_error)

    verifier = jwt_module.SynapseJWTVerifier(
        jwks_uri="http://example/jwks",
        issuer="issuer",
        audience="client",
    )

    result = verifier._verify_token_sync("token")  # type: ignore[attr-defined]
    assert result is None
