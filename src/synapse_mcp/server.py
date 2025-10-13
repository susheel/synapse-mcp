#!/usr/bin/env python3
"""
Synapse MCP server using FastMCP with per-connection authentication.
"""

# Import the MCP instance with all tools already defined
from synapse_mcp import mcp

# The server is now fully configured with per-connection authentication
# Diagnostics are printed during app initialization

# This will be imported by __main__.py
app = mcp