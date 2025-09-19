#!/usr/bin/env python3
"""
Synapse MCP server using proper FastMCP structure.
"""

# Import the MCP instance with all tools already defined
from synapse_mcp import mcp, initialize_authentication

# The server is already fully configured in __init__.py with all @mcp.tool decorators
# We just need to set up authentication and run it properly

def initialize_server():
    """Initialize the server with unified authentication."""
    # Initialize authentication (PAT if available, otherwise prepare for OAuth)
    try:
        auth_initialized, using_pat = initialize_authentication()
        if using_pat:
            print("Server initialized with PAT authentication")
        else:
            print("Server initialized - OAuth authentication will be required for protected resources")
    except Exception as e:
        print(f"Authentication initialization failed: {e}")

# This will be imported by __main__.py
app = mcp