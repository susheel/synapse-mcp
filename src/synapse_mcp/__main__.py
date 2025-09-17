#!/usr/bin/env python3
"""
Main entry point for running the Synapse MCP server.
"""

import argparse
import logging
import sys
import uvicorn
import os
from synapse_mcp import mcp, server

def main():
    """Run the Synapse MCP server."""
    parser = argparse.ArgumentParser(description="Run the Synapse MCP server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Log server information
    logger = logging.getLogger("synapse_mcp")
    logger.info(f"Starting Synapse MCP server on {args.host}:{args.port}")

    # Set the server URL
    server_url = os.environ.get("MCP_SERVER_URL", f"mcp://{args.host}:{args.port}")
    mcp.server_url = server_url

    # Run the server using uvicorn
    try:
        uvicorn.run(
            server.app,
            host=args.host,
            port=args.port,
            reload=args.debug
        )
        logger.info("Server stopped")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
