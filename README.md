# Synapse MCP Server

A Model Context Protocol (MCP) server that enables AI agent access to Synapse entities (Datasets, Projects, Folders, Files, Tables, and more).

You (your AI agent) can:
- Retrieve entities by ID
- Retrieve entities by name
- Get entity annotations
- Get entity children
- Query entities based on various criteria
- Query Synapse tables
- Get datasets in Croissant metadata format

## Usage

This guide provides typical user instructions for connecting to the Synapse MCP server. For contributor setup, please see [DEVELOPMENT.md](./DEVELOPMENT.md).

### Authentication

The Synapse MCP server supports two authentication methods:

1.  **OAuth2 (Default):** This is the primary and recommended authentication method. It provides a secure, browser-based login flow. When your AI agent needs to access protected resources, it will prompt you to log in to Synapse in your browser. This method is used by default for both local and remote servers.

2.  **Personal Access Token (PAT):** This method is available for local development or in environments where a browser-based login is not feasible. It requires you to provide a Synapse Personal Access Token to the server.

### Connecting to the Server

#### Remote Server (Beta)

You can connect to our deployed remote server, which skips the need for local installation. Authentication is handled via the default OAuth2 flow.

**Configure Your AI Client:**

*   *Claude Code:**
    ```bash
    # Add the remote server
    claude mcp add --transport http synapse -- https://synapse-mcp.fly.dev/mcp
    ```
    When you attempt to access a private Synapse resource, the client will automatically guide you through the browser login process.

#### Local Server

For development or console-only use, you can run the server on your local machine.

**1. Install the Package:**
```bash
pip install synapse-mcp
```

**2. Run the Server:**

*   **For OAuth2 (Default):** Simply start the server.
    ```bash
    synapse-mcp --port 9000
    ```

*   **For Personal Access Token (PAT):** For using PAT, first generate one from your Synapse account settings. Then, start the server with the `SYNAPSE_PAT` environment variable set.
    ```bash
    export SYNAPSE_PAT="YOUR_TOKEN_HERE"
    synapse-mcps
    ```

**3. Configure Your AI Client:**

*   **Claude Code:**
    ```bash
    # Add your local server (ensure you use the full URL)
    claude mcp add --transport http synapse -- http://127.0.0.1:9000
    ```

*   **Claude Desktop (Using PAT):** If you are using PAT authentication with the local server, you can configure Claude Desktop to pass the token.
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

### Example Prompts

Once connected, you can use Synapse data in your conversations:
- "Create a chart from the data in Synapse table syn123456"
- "Query all files in the Synapse project syn123456"
- "Get annotations for the Synapse entity syn123456"

## Contributing

Contributions are welcome! Please see our [Development Guide](./DEVELOPMENT.md) for instructions on setting up a development environment, running tests, and more.

## License

MIT
