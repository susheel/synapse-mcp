#!/usr/bin/env python3
"""
Example client for the Synapse MCP server.

This client demonstrates how to interact with the Synapse MCP server
using simple HTTP requests.
"""

import os
import sys
import json
import requests
import getpass

class SynapseMCPClient:
    """A client for the Synapse MCP server."""
    
    def __init__(self, server_url):
        """Initialize with the server URL."""
        self.server_url = server_url
    
    def get_info(self):
        """Get server info."""
        url = f"{self.server_url}/info"
        response = requests.get(url)
        return response.json()
    
    def list_tools(self):
        """List available tools."""
        url = f"{self.server_url}/tools"
        response = requests.get(url)
        return response.json()
    
    def list_resources(self):
        """List available resources."""
        url = f"{self.server_url}/resources"
        response = requests.get(url)
        return response.json()
    
    def use_tool(self, tool_name, params):
        """Use an MCP tool."""
        url = f"{self.server_url}/tools/{tool_name}"
        response = requests.post(url, json=params)
        return response.json()
    
    def access_resource(self, resource_uri, params=None):
        """Access an MCP resource."""
        # Convert URI to URL path
        path = resource_uri.replace('://', '/').replace(':', '/')
        url = f"{self.server_url}/resources/{path}"
        response = requests.get(url, params=params)
        return response.json()

def main():
    """Run the example client."""
    # Connect to the server
    client = SynapseMCPClient("http://127.0.0.1:9000")
    
    # Get server info
    print("Getting server info...")
    info = client.get_info()
    print(f"Server name: {info.get('name')}")
    print(f"Server URL: {info.get('url')}")
    print(f"Server version: {info.get('version')}")
    
    # List available tools
    print("\nListing available tools...")
    tools = client.list_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"- {tool.get('name')}: {tool.get('description')}")
    
    # List available resources
    print("\nListing available resources...")
    resources = client.list_resources()
    print(f"Available resources: {len(resources)}")
    for resource in resources:
        print(f"- {resource.get('pattern')}: {resource.get('description')}")
    
    # Authenticate with Synapse using real credentials
    print("\nAuthenticating with Synapse...")
    # Get Synapse credentials from user
    auth_token = getpass.getpass("Enter your Synapse auth token: ")
    
    auth_result = client.use_tool("authenticate", {
        "auth_token": auth_token
    })
    
    if not auth_result.get("success", False):
        print(f"Authentication failed: {auth_result.get('message', 'Unknown error')}")
        sys.exit(1)
    
    print("Authentication successful!")
    
    # Example 1: Get a project by ID
    # Replace with a real Synapse project ID
    project_id = input("Enter a Synapse project ID: ")
    print(f"\nGetting project {project_id}...")
    project = client.use_tool("get_entity", {"entity_id": project_id})
    print(json.dumps(project, indent=2))
    
    # Example 2: Get annotations for the project
    print(f"\nGetting annotations for project {project_id}...")
    annotations = client.use_tool("get_entity_annotations", {"entity_id": project_id})
    print(json.dumps(annotations, indent=2))
    
    # Example 3: Get children of the project
    print(f"\nGetting children of project {project_id}...")
    children = client.use_tool("get_entity_children", {"entity_id": project_id})
    print(f"Found {len(children)} children")
    for child in children:
        print(f"- {child.get('name', 'Unknown')} ({child.get('id', 'Unknown')})")
    
    # Example 4: Query for files in the project
    print("\nQuerying for files...")
    files = client.use_tool("query_entities", {"entity_type": "file"})
    print(f"Found {len(files)} files")
    for file in files:
        print(f"- {file.get('name', 'Unknown')} ({file.get('id', 'Unknown')})")
    
    # Example 5: Query a table (if available)
    # Replace with a real Synapse table ID
    table_id = input("Enter a Synapse table ID: ")
    print(f"\nQuerying table {table_id}...")
    query = f"SELECT * FROM {table_id} LIMIT 10"
    table_data = client.use_tool("query_table", {"table_id": table_id, "query": query})
    print(json.dumps(table_data, indent=2))

if __name__ == "__main__":
    main()