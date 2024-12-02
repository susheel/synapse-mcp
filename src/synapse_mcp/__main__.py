#!/usr/bin/env python3
"""
Main entry point for running the Synapse MCP server.
"""

import argparse
import logging
import sys
import uvicorn
import os
import importlib.util

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

    # Determine the path to the server.py file
    # First check if it's in the current directory
    if os.path.exists("server.py"):
        server_path = "server.py"
    else:
        # Otherwise use the one from the package
        package_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(os.path.dirname(package_dir), "server.py")
    
    # Import the server module
    if os.path.exists(server_path):
        spec = importlib.util.spec_from_file_location("server", server_path)
        if spec and spec.loader:
            server = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(server)
            
            # Run the server using uvicorn
            try:
                # Use uvicorn to run the FastAPI app
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
        else:
            logger.error(f"Failed to load server module from {server_path}")
            sys.exit(1)
    else:
        logger.error(f"Server file not found at {server_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()