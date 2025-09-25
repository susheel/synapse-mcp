# Synapse MCP Server

A Model Context Protocol (MCP) server that enables AI agent access to Synapse entities (Datasets, Projects, Folders, Files, Tables, and more).

You (your AI agent) can:
- Retrieve entities by ID
- Get entity annotations
- List entity children
- Search Synapse entities with path and type filters

## Available Tools

| Tool | Description |
| --- | --- |
| `get_entity(entity_id)` | Fetch core metadata for a Synapse entity by ID. |
| `get_entity_annotations(entity_id)` | Return custom annotations associated with an entity. |
| `get_entity_children(entity_id)` | List children for container entities such as projects and folders. |
| `search_synapse(query_term=None, ...)` | Search Synapse entities by keyword with optional name/type/parent filters. Results are provided by Synapse as data custodian; attribution and licensing follow the source entity metadata. |

> Resources such as `entities/{id_or_name}` remain available for name-based lookups and table helpers.

## Available Resources

Resources return ready-to-present entity metadata. Use tools when you need searches,
children listings, or other derived results.

| Resource | Description |
| --- | --- |
| `entities/{id_or_name}` | Resolve an entity by Synapse ID or by name (best-effort search). |
| `entities/{id}/annotations` | Retrieve annotation key/value pairs for an entity. |
| `projects/{id_or_name}` | Resolve a project by ID or name. |
| `projects/{id}/annotations` | Retrieve annotations for a project. |
| `datasets/{id_or_name}` | Resolve a dataset by ID or name. |
| `datasets/{id}/annotations` | Retrieve annotations for a dataset. |
| `folders/{id_or_name}` | Resolve a folder by ID or name. |
| `folders/{id}/annotations` | Retrieve annotations for a folder. |
| `files/{id_or_name}` | Resolve a file by ID or name. |
| `files/{id}/annotations` | Retrieve annotations for a file. |
| `tables/{id_or_name}` | Resolve a table by ID or name. |
| `tables/{id}/annotations` | Retrieve annotations for a table. |

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
