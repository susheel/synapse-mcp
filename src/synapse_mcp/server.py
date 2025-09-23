#!/usr/bin/env python3
"""
Synapse MCP server using FastMCP with per-connection authentication.
"""

# Import the MCP instance with all tools already defined
from synapse_mcp import mcp

# The server is now fully configured with per-connection authentication
# No global authentication initialization needed

def initialize_server():
    """Initialize the server (now using per-connection auth)."""
    print("Server initialized with per-connection authentication architecture")
    print("- Each connection maintains its own synapseclient instance")
    print("- Authentication is handled per-connection (PAT or OAuth)")
    print("- Multi-user isolation ensures production-ready security")

# This will be imported by __main__.py
app = mcp