"""Factory for building the Synapse OAuth proxy."""

import logging
from typing import Optional

from .config import OAuthSettings, load_oauth_settings, should_skip_oauth
from .jwt import SynapseJWTVerifier
from .proxy import SessionAwareOAuthProxy

logger = logging.getLogger("synapse_mcp.auth")


def create_oauth_proxy(env: Optional[dict[str, str]] = None):
    if should_skip_oauth(env):
        print("SYNAPSE_PAT detected - skipping OAuth configuration")
        return None

    settings = load_oauth_settings(env)
    if not settings:
        print("OAuth configuration missing - running without authentication")
        return None

    jwt_verifier = SynapseJWTVerifier(
        jwks_uri="https://repo-prod.prod.sagebase.org/auth/v1/oauth2/jwks",
        issuer="https://repo-prod.prod.sagebase.org/auth/v1",
        audience=settings.client_id,
        algorithm="RS256",
        required_scopes=["view", "download", "modify"],
    )

    auth = SessionAwareOAuthProxy(
        upstream_authorization_endpoint="https://signin.synapse.org",
        upstream_token_endpoint="https://repo-prod.prod.sagebase.org/auth/v1/oauth2/token",
        upstream_client_id=settings.client_id,
        upstream_client_secret=settings.client_secret,
        redirect_path="/oauth/callback",
        token_verifier=jwt_verifier,
        base_url=settings.server_url,
    )

    return auth


__all__ = ["create_oauth_proxy"]
