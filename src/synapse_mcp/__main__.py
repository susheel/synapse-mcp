#!/usr/bin/env python3
"""
Main entry point for running the Synapse MCP server.
"""

import argparse
import logging
import sys
import os

def main():
    """Run the Synapse MCP server."""
    parser = argparse.ArgumentParser(description="Run the Synapse MCP server")
    parser.add_argument("--host", help="Host to bind to (for HTTP transport)")
    parser.add_argument("--port", type=int, help="Port to listen on (for HTTP transport)")
    parser.add_argument("--http", action="store_true", help="Use HTTP transport instead of default stdio")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Determine transport mode
    transport_env = os.environ.get("MCP_TRANSPORT", "").lower()

    # Determine the actual transport to use
    if args.http or transport_env in ["sse", "streamable-http"]:
        if transport_env == "sse":
            transport = "sse"
        else:
            transport = "streamable-http"
        use_http = True
    elif transport_env == "stdio":
        transport = "stdio"
        use_http = False
    else:
        # Default to stdio for MCP clients
        transport = "stdio"
        use_http = False

    # Log server information
    logger = logging.getLogger("synapse_mcp")
    if use_http:
        host = args.host or os.environ.get("HOST", "127.0.0.1")
        port = args.port or int(os.environ.get("PORT", "9000"))
        logger.info(f"Starting Synapse MCP server on {host}:{port} with {transport} transport")
    else:
        logger.info("Starting Synapse MCP server with STDIO transport")

    # Import after environment is set up
    # Authentication is configured during module import
    from synapse_mcp import mcp

    # Use FastMCP's built-in server runner
    try:
        logger.info("Running FastMCP server")
        # Only set HOST/PORT for HTTP transports
        if use_http:
            os.environ["HOST"] = args.host or os.environ.get("HOST", "127.0.0.1")
            os.environ["PORT"] = str(args.port or int(os.environ.get("PORT", "9000")))

        if use_http:
            host = args.host or os.environ.get("HOST", "127.0.0.1")
            port = args.port or int(os.environ.get("PORT", "9000"))
            mcp.run(transport=transport, host=host, port=port)
        else:
            mcp.run(transport=transport)
        logger.info("Server stopped")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
