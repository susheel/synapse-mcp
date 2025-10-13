"""Core MCP application setup."""

from datetime import datetime, timezone
import logging
import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .oauth import create_oauth_proxy
from .auth_middleware import OAuthTokenMiddleware, PATAuthMiddleware

logger = logging.getLogger("synapse_mcp.app")

# Determine authentication mode and configure server accordingly
auth = create_oauth_proxy()
has_pat = bool(os.environ.get("SYNAPSE_PAT"))
has_oauth = bool(
    os.environ.get("SYNAPSE_OAUTH_CLIENT_ID")
    and os.environ.get("SYNAPSE_OAUTH_CLIENT_SECRET")
)

# Server instructions
_INSTRUCTIONS = (
    "Synapse is a collaborative data platform for researchers where data is organized in public or private projects. "
    "Synapse MCP Server helps users discover and understand Synapse data that they can see, providing tools for: "
    "searches, wiki retrieval, metadata retrieval, and project traversal (through projects/folders). "
    "Review entity metadata for attribution and licensing. "
    "Each connection must authenticate with a Synapse."
)

if auth and has_oauth:
    # Production mode: OAuth authentication
    mcp = FastMCP("Synapse MCP Server", instructions=_INSTRUCTIONS, auth=auth)
    mcp.add_middleware(OAuthTokenMiddleware())
    logger.info("Server configured for OAuth authentication (production mode)")
    print("🔐 OAuth authentication configured (production mode)")

    if has_pat:
        logger.warning(
            "Both SYNAPSE_PAT and OAuth credentials detected. "
            "Using OAuth (production mode). "
            "Remove SYNAPSE_OAUTH_CLIENT_ID/SECRET to use PAT mode."
        )
        print("⚠️  Warning: SYNAPSE_PAT ignored in OAuth mode")

elif has_pat:
    # Development mode: PAT authentication
    mcp = FastMCP("Synapse MCP Server", instructions=_INSTRUCTIONS, auth=None)
    mcp.add_middleware(PATAuthMiddleware())
    logger.info("Server configured for PAT authentication (development mode)")
    print("🔧 PAT authentication configured (development mode)")

else:
    # No authentication configured
    raise ValueError(
        "No authentication configured. Set one of:\n"
        "  Production (OAuth): SYNAPSE_OAUTH_CLIENT_ID + SYNAPSE_OAUTH_CLIENT_SECRET\n"
        "  Development (PAT):  SYNAPSE_PAT"
    )


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Standard HTTP health check endpoint for Kubernetes and monitoring systems."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "synapse-mcp",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "version": "0.2.0",
            "is_oauth_configured": bool(
                os.environ.get("SYNAPSE_OAUTH_CLIENT_ID")
                and os.environ.get("SYNAPSE_OAUTH_CLIENT_SECRET")
            ),
        }
    )


__all__ = ["auth", "mcp", "health_check"]
