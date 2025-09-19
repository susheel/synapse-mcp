#!/usr/bin/env python3
"""
Synapse MCP server using proper FastMCP structure.
"""

# Import the MCP instance with all tools already defined
from synapse_mcp import mcp
from synapse_mcp import pat_auth_manager

# The server is already fully configured in __init__.py with all @mcp.tool decorators
# We just need to set up authentication and run it properly

def initialize_server():
    """Initialize the server with authentication."""
    # Initialize PAT auth if available (optional for OAuth-only deployments)
    try:
        pat_auth_manager.initialize_pat_auth()
    except Exception as e:
        print(f"PAT authentication initialization failed (continuing with OAuth-only): {e}")

# This will be imported by __main__.py
app = mcp