# Synapse MCP Server

A Model Context Protocol (MCP) server that enables AI agent access to Synapse entities (Datasets, Projects, Folders, Files, Tables, and more).

You (your AI agent) can:
- Retrieve entities by ID
- Get entity annotations
- List entity children
- Search Synapse entities with path and type filters
- Inspect provenance/activity recorded for an entity version

## Available Tools

| Tool | Friendly Name | Description |
| --- | --- | --- |
| `get_entity(entity_id)` | Fetch Entity | Fetch core metadata for a Synapse entity by ID. |
| `get_entity_annotations(entity_id)` | Fetch Entity Annotations | Return custom annotations associated with an entity. |
| `get_entity_provenance(entity_id, version=None)` | Fetch Entity Provenance | Retrieve provenance (activity) metadata for an entity, optionally scoped to a specific version. |
| `get_entity_children(entity_id)` | List Entity Children | List children for container entities such as projects and folders. |
| `search_synapse(query_term=None, ...)` | Search Synapse | Search Synapse entities by keyword with optional name/type/parent filters. Results are provided by Synapse as data custodian; attribution and licensing follow the source entity metadata. |

## Available Resources

Resources provide ready-to-present context that clients can pull without extra parameters. When you need to search or compute derived results, prefer tools instead.

| Resource | Friendly Name | Description |
| --- | --- | --- |
| `synapse://guides/user-account-types` | Synapse Account Types | Markdown summary of Synapse user account types and their capabilities. |

## Usage

This guide provides typical user instructions for connecting to the Synapse MCP server. For contributor setup, please see [DEVELOPMENT.md](./DEVELOPMENT.md).

### Authentication

The Synapse MCP server supports two authentication methods:

1.  **OAuth2 (Default):** This is the primary and recommended authentication method. It provides a secure, browser-based login flow. When your AI agent needs to access protected resources, it will prompt you to log in to Synapse in your browser. This method is used by default for both local and remote servers.

2.  **Personal Access Token (PAT):** This method is available for local development or in environments where a browser-based login is not feasible. It requires you to provide a Synapse Personal Access Token to the server.

### Using the MCP Server

#### Local Server

**1. Install the Package:**
```bash
pip install synapse-mcp
```

**2. Configure Your AI Client:**

The setup depends on which transport method you need:

**Claude Code with local stdio transport (default):**

The client automatically starts the server process:
```bash
claude mcp add synapse -- env SYNAPSE_PAT="YOUR_TOKEN_HERE" synapse-mcp
```

**Claude Desktop:**

The client automatically starts the server process:
1.  Open Claude Desktop Settings > Developer > Edit Config.
2.  Add the following to `mcpServers`:
    ```json
    "synapse": {
      "command": "synapse-mcp",
      "env": {
        "SYNAPSE_PAT": "YOUR_TOKEN_HERE"
      }
    }
    ```
3.  Save the file and restart Claude Desktop.

#### Remote Server (WIP)

Developments are underway for making synapse-mcp available as a remote server. See DEVELOPMENT.md if you would like to contribute. Stay tuned.


### Example Prompts

Once connected, you can use Synapse data in your conversations:
- "Create a chart from the data in Synapse table syn123456"
- "Query all files in the Synapse project syn123456"
- "Get annotations for the Synapse entity syn123456"

## Contributing

Contributions are welcome! Please see our [Development Guide](./DEVELOPMENT.md) for instructions on setting up a development environment, running tests, and more.

## License

MIT
