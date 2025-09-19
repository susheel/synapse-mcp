"""
FastMCP OAuth proxy configuration for Synapse authentication.
"""

import os
import base64
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastmcp.server.auth import OAuthProxy

# Set up logging for token debugging
logger = logging.getLogger("synapse_mcp.auth")

class SynapseJWTVerifier:
    """Custom JWT verifier for Synapse tokens that returns FastMCP-compatible results"""

    def __init__(self, jwks_uri: str, issuer: str, audience: str, algorithm: str = "RS256", required_scopes: Optional[List[str]] = None):
        self.jwks_uri = jwks_uri
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.required_scopes = required_scopes or []
        self._jwks_cache = None

    async def _get_jwks(self):
        """Get JWKS from Synapse endpoint"""
        if self._jwks_cache is None:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri)
                self._jwks_cache = response.json()
        return self._jwks_cache

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Synapse JWT token and return access token info"""
        try:
            import jwt
            from jwt.exceptions import InvalidTokenError
            from cryptography.hazmat.primitives import serialization

            logger.info("Starting Synapse JWT verification")

            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')

            # Get JWKS and find the right key
            jwks = await self._get_jwks()
            key = None
            for jwk in jwks['keys']:
                if jwk['kid'] == kid:
                    # Convert JWK to public key
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    key = public_key
                    break

            if not key:
                logger.error(f"No key found for kid: {kid}")
                return None

            # Decode and verify token
            decoded = jwt.decode(
                token,
                key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )

            logger.info(f"JWT Payload: {decoded}")

            # Extract scopes from Synapse's nested structure
            scopes = []
            if 'access' in decoded and 'scope' in decoded['access']:
                scopes = decoded['access']['scope']
                logger.info(f"Extracted scopes from access.scope: {scopes}")

            # Check required scopes
            if self.required_scopes:
                token_scopes = set(scopes)
                required_scopes = set(self.required_scopes)
                if not required_scopes.issubset(token_scopes):
                    logger.warning(f"Required scopes {required_scopes} not found in token scopes {token_scopes}")
                    return None

            # Authenticate the global Synapse client with this access token
            from synapse_mcp import authenticate_synapse_client
            authenticate_synapse_client(token)

            # Return FastMCP-compatible access token object
            from types import SimpleNamespace

            access_token = SimpleNamespace()
            access_token.sub = decoded.get("sub")
            access_token.scopes = scopes
            access_token.claims = decoded
            access_token.token = token
            access_token.expires_at = decoded.get("exp", 0)  # Add expires_at attribute
            access_token.client_id = decoded.get("aud")  # Use audience as client_id

            return access_token

        except InvalidTokenError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in Synapse JWT verification: {e}")
            return None

def create_oauth_proxy():
    """Create OAuth proxy for Synapse authentication."""
    # Import here to avoid circular imports
    from synapse_mcp import initialize_authentication

    # Check if PAT authentication is successful
    auth_initialized, using_pat = initialize_authentication()
    if using_pat and auth_initialized:
        print("PAT authentication successful - skipping OAuth configuration")
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

    # Configure custom JWT verifier for Synapse access tokens
    jwt_verifier = SynapseJWTVerifier(
        jwks_uri="https://repo-prod.prod.sagebase.org/auth/v1/oauth2/jwks",
        issuer="https://repo-prod.prod.sagebase.org/auth/v1",
        audience=client_id,
        algorithm="RS256",
        required_scopes=["view", "download", "modify"]
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
        upstream_token_endpoint="https://repo-prod.prod.sagebase.org/auth/v1/oauth2/token",
        upstream_client_id=client_id,
        upstream_client_secret=client_secret,
        redirect_path=redirect_path,
        token_verifier=jwt_verifier,
        base_url=server_url
    )

    return auth