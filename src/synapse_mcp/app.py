"""Core MCP application setup."""

from datetime import datetime, timezone
import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .oauth import create_oauth_proxy
from .auth_middleware import OAuthTokenMiddleware

# Instantiate the FastMCP server with optional OAuth proxy
auth = create_oauth_proxy()
mcp = FastMCP("Synapse MCP Server", auth=auth)

# Ensure per-connection tokens are routed into the request context
mcp.add_middleware(OAuthTokenMiddleware())


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


def initialize_server() -> None:
    """Emit diagnostics for the new per-connection authentication architecture."""
    print("Server initialized with per-connection authentication architecture")
    print("- Each connection maintains its own synapseclient instance")
    print("- Authentication is handled per-connection (PAT or OAuth)")
    print("- Multi-user isolation ensures production-ready security")


__all__ = ["auth", "mcp", "health_check", "initialize_server"]
