"""
FastMCP OAuth proxy configuration for Synapse authentication.
"""

import os
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier

def create_oauth_proxy():
    """Create OAuth proxy for Synapse authentication."""
    # Skip OAuth if PAT is provided
    synapse_pat = os.environ.get("SYNAPSE_PAT")
    if synapse_pat:
        print(f"SYNAPSE_PAT detected - skipping OAuth configuration")
        return None

    # Get OAuth configuration from environment
    client_id = os.environ.get("SYNAPSE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("SYNAPSE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.environ.get("SYNAPSE_OAUTH_REDIRECT_URI")
    server_url = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:9000")

    # For streamable-http transport, OAuth endpoints are at root level
    # Remove /mcp suffix if present to ensure OAuth endpoints work
    if server_url.endswith("/mcp"):
        server_url = server_url[:-4]

    if not all([client_id, client_secret, redirect_uri]):
        print("OAuth configuration missing - running without authentication")
        return None

    # Configure JWT verifier for Synapse tokens
    jwt_verifier = JWTVerifier(
        # Synapse uses RS256 for JWT signing
        algorithm="RS256",
        # Use Synapse's JWKS endpoint for public key verification
        jwks_uri="https://repo-prod.prod.sagebase.org/auth/v1/oauth2/jwks",
        # Required scopes for Synapse API access
        required_scopes=["openid", "view", "download", "offline_access"]
    )

    # Configure redirect path to match registered Synapse OAuth client
    # FastMCP default is /auth/callback, but we need /oauth/callback to match registration
    redirect_path = "/oauth/callback"

    # Create OAuth proxy pointing to Synapse OAuth endpoints
    # Available scopes: https://rest-docs.synapse.org/rest/org/sagebionetworks/repo/model/oauth/OAuthScope.html
    # - openid: Required scope for OpenID Connect
    # - email: Returns email claims when used with 'openid'
    # - profile: Returns user profile information when used with 'openid'
    # - ga4gh_passport_v1: Returns GA4GH Passport when used with 'openid'
    # - view: Read object metadata
    # - download: Download data
    # - modify: Create or change content
    # - authorize: Authorize access and share resources
    # - offline_access: Access resources when user is not logged in
    auth = OAuthProxy(
        upstream_authorization_endpoint="https://signin.synapse.org",
        upstream_token_endpoint="https://auth.synapse.org/oauth2/token",
        upstream_client_id=client_id,
        upstream_client_secret=client_secret,
        redirect_path=redirect_path,
        token_verifier=jwt_verifier,
        base_url=server_url
    )

    return auth