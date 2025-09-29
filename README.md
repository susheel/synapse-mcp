# Synapse MCP Server

![synapse_wordmark](https://github.com/user-attachments/assets/7baf44ab-1b77-482d-b96f-84d3cb1dbdc9)

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
| `synapse://feeds/blog` | Sage Blog RSS | Live RSS XML for the latest Sage Bionetworks publication posts. |

## Usage

This guide provides typical user instructions for connecting to the Synapse MCP server. For contributor setup, please see [DEVELOPMENT.md](./DEVELOPMENT.md).

### Authentication

The Synapse MCP server supports two authentication methods:

1.  **OAuth2 (Default):** This is the primary and recommended authentication method. It provides a secure, browser-based login flow. When your AI agent needs to access protected resources, it will prompt you to log in to Synapse in your browser. This method is used by default for both local and remote servers.

2.  **Personal Access Token (PAT):** This method is available for local development or in environments where a browser-based login is not feasible. It requires you to provide a Synapse Personal Access Token to the server.

### MCP Server setup

#### Remote Server

Use this URL in your client:
🔌 https://mcp.synapse.org/mcp

##### Claude Desktop Instructions

Go to Settings > Connectors > Add custom connector

<img width="664" height="146" alt="image" src="https://github.com/user-attachments/assets/fcfe54ba-1c1c-4fa8-9bae-c198cffff6ce" />

##### Claude Code

`claude mcp add --transport http synapse -- https://mcp.synapse.org/mcp`

#### Local Server

For running local server, see [DEVELOPMENT.md](./DEVELOPMENT.md)

### Example Prompts

See [usage examples](./doc/usage.md)

## Contributing

Contributions are welcome! Please see our [Development Guide](./DEVELOPMENT.md) for instructions on setting up a development environment, running tests, and more.

## License

 **MIT**

## Contact

![synapse_icon](https://github.com/user-attachments/assets/b629f426-ae1b-4179-87d2-ac2c73419644)

For issues, please file an issue. For other contact, see https://sagebionetworks.org/contact.

