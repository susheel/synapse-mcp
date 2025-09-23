"""Environment helpers for OAuth configuration."""

from dataclasses import dataclass
import logging
import os
from typing import Mapping, Optional

logger = logging.getLogger("synapse_mcp.oauth")


@dataclass
class OAuthSettings:
    client_id: str
    client_secret: str
    server_url: str
    redirect_uri: str


DEFAULT_SERVER_URL = "http://127.0.0.1:9000"
REDIRECT_SUFFIX = "/oauth/callback"


def should_skip_oauth(env: Optional[Mapping[str, str]] = None) -> bool:
    env = _ensure_env(env)
    return bool(env.get("SYNAPSE_PAT"))


def load_oauth_settings(env: Optional[Mapping[str, str]] = None) -> Optional[OAuthSettings]:
    env = _ensure_env(env)

    client_id = env.get("SYNAPSE_OAUTH_CLIENT_ID")
    client_secret = env.get("SYNAPSE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    server_url = _sanitise_server_url(env.get("MCP_SERVER_URL", DEFAULT_SERVER_URL))
    redirect_uri = _resolve_redirect_uri(server_url, env.get("SYNAPSE_OAUTH_REDIRECT_URI"))

    return OAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        server_url=server_url,
        redirect_uri=redirect_uri,
    )


def _ensure_env(env: Optional[Mapping[str, str]]) -> Mapping[str, str]:
    return env if env is not None else os.environ


def _sanitise_server_url(raw_url: str) -> str:
    url = _normalise_loopback(raw_url)
    if url.endswith("/mcp"):
        url = url[:-4]
    return url


def _resolve_redirect_uri(server_url: str, raw_redirect: Optional[str]) -> str:
    if raw_redirect:
        redirect = _normalise_loopback(raw_redirect)
        logger.info("Using provided redirect URI: %s", redirect)
        return redirect

    redirect = f"{server_url}{REDIRECT_SUFFIX}"
    logger.info("Auto-generated redirect URI: %s", redirect)
    return redirect


def _normalise_loopback(url: str) -> str:
    if "localhost" in url:
        normalised = url.replace("localhost", "127.0.0.1")
        logger.info("Normalised loopback host from localhost to 127.0.0.1: %s", normalised)
        return normalised
    return url


__all__ = ["OAuthSettings", "should_skip_oauth", "load_oauth_settings", "DEFAULT_SERVER_URL", "REDIRECT_SUFFIX"]
