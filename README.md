# Synapse MCP Server

A Model Context Protocol (MCP) server that exposes Synapse Entities (Datasets, Projects, Folders, Files, Tables) with their annotations and supports OAuth2 authentication.

## Overview

This server provides a RESTful API for accessing Synapse entities and their annotations through the Model Context Protocol (MCP). It allows you to:

- Authenticate with Synapse
- Retrieve entities by ID
- Retrieve entities by name
- Get entity annotations
- Get entity children
- Query entities based on various criteria
- Query Synapse tables
- Get datasets in Croissant metadata format

## Usage

Below shows the simplest setup options for you to get started with the Synapse MCP server as a research/scientific user. 
For contributor-centric installation, please see DEVELOPMENT.md.

### Local Server Usage

#### Install Python Package

```
pip install synapse-mcp
```

#### Understand Authenticated vs. Non-Authenticated Usage

With local MCP servers, authentication can be optional. 
You can search for resources on Synapse and download a limited subset without providing Synapse account credentials. 

But we recommend you create a Synapse account if you don't already have one and provide a Personal Access Token (PAT) for authenticated local usage. 
The PAT can be generated from your account settings. 
This allows your AI agent to access much more, including any private data that is shared with you. 
In non-authenticated usage, your agent will say that it can't access resources because you are logged in. 
See below for how to provide authentication when configure your client.

### Configure Your AI Client of Choice

Configuration instructions shown below for some popular clients.

#### Claude Desktop

- Open Claude Desktop
- Click on the Claude menu and select "Settings..."
- Click on "Developer" in the left-hand bar
- Click on "Edit Config"
- Add the following configuration to the `mcpServers` section:

```json
"synapse": {
  "command": "synapse-mcp",
  "env": {
    "SYNAPSE_PAT": "YOUR_TOKEN_HERE"
  }
}
```
- Save the configuration file and restart Claude Desktop

Behind the scenes, Claude Desktops starts the server at default ports with the command:

```bash
synapse-mcp
```

#### Claude Code

Here, we provide `--env SYNAPSE_PAT` for authenticated use.

`claude mcp add synapse --env SYNAPSE_PAT=$SYNAPSE_AUTH_TOKEN -- synapse-mcp`


#### Others

TBD


### Remote Server Usage (Beta)

You can connect to our deployed remote server, skipping the installation step. 
However, remote server requires authentication through OAuth2 flow, so it is presumed you have a Synapse account that you can log into. 
Your browser will be redirected to Synapse.org to grant access to your client. 

### Configure Your AI Client of Choice

#### Claude Code

TODO

#### codename Goose

TODO

#### Example Prompts

You can now use Synapse data in your conversations with Claude. For example:
- "Get the entity with ID syn123456 from Synapse"
- "Query all files in the Synapse project syn123456"
- "Get annotations for the Synapse entity syn123456"

## Contributing

Contributions are welcome! For instructions on how to set up a local development environment, run tests, and test the OAuth flow, please see our [Development Guide](./DEVELOPMENT.md).

## License

MIT
