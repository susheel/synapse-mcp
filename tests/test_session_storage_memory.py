"""Tests for in-memory session storage guardrails."""

from datetime import datetime, timedelta, timezone
import logging

import pytest

from synapse_mcp.session_storage.memory import InMemorySessionStorage


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_warn_threshold_triggers(caplog):
    storage = InMemorySessionStorage(max_tokens=3, warn_fraction=0.5)
    caplog.set_level(logging.WARNING, "synapse_mcp.session_storage")

    await storage.set_user_token("user-1", "token-1")
    assert "nearing capacity" not in caplog.text

    await storage.set_user_token("user-2", "token-2")
    assert "nearing capacity" in caplog.text


@pytest.mark.anyio
async def test_max_capacity_warning_resets_after_removal(caplog):
    storage = InMemorySessionStorage(max_tokens=2, warn_fraction=0.5)
    caplog.set_level(logging.WARNING, "synapse_mcp.session_storage")

    await storage.set_user_token("user-1", "token-1")
    await storage.set_user_token("user-2", "token-2")
    assert "reached configured maximum" in caplog.text

    caplog.clear()
    await storage.remove_user_token("user-1")
    await storage.set_user_token("user-3", "token-3")
    assert "reached configured maximum" in caplog.text


@pytest.mark.anyio
async def test_cleanup_updates_usage_flags(caplog):
    storage = InMemorySessionStorage(max_tokens=2, warn_fraction=0.5)
    caplog.set_level(logging.WARNING, "synapse_mcp.session_storage")

    await storage.set_user_token("user-1", "token-1")
    await storage.set_user_token("user-2", "token-2")

    # Force expiry
    expired_time = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    storage._token_metadata["token-2"]["expires_at"] = expired_time

    caplog.clear()
    await storage.cleanup_expired_tokens()
    assert caplog.text == ""

    caplog.clear()
    await storage.set_user_token("user-3", "token-3")
    assert "reached configured maximum" in caplog.text
