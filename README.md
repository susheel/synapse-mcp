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

## Installation

```bash
# Clone the repository
git clone https://github.com/SageBionetworks/synapse-mcp.git
cd synapse-mcp

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Installing from PyPI

```bash
# Install from PyPI
pip install synapse-mcp
```

## Usage

### Starting the Server

```bash
python server.py --host 127.0.0.1 --port 9000
```

This will start the MCP server on the default port (9000).

### Using the CLI

```bash
# Start the server using the CLI
synapse-mcp --host 127.0.0.1 --port 9000 --debug
```

### Command-line Options

```
usage: server.py [-h] [--host HOST] [--port PORT] [--debug]

Run the Synapse MCP server with OAuth2 support

options:
  -h, --help       show this help message and exit
  --host HOST      Host to bind to
  --port PORT      Port to listen on
  --debug          Enable debug logging
  --server-url URL Public URL of the server (for OAuth2 redirect)
```

### Running Tests

```bash
# Run all tests with coverage
./run_tests.sh

# Or run pytest directly
python -m pytest
```

### Testing the Server

```bash
python examples/client_example.py
```

## Authentication Methods

### Environment Variables

The server supports the following environment variables:

- `HOST`: The host to bind to (default: 127.0.0.1)
- `PORT`: The port to listen on (default: 9000)
- `MCP_TRANSPORT`: The transport protocol to use (default: stdio)
  - `stdio`: Use standard input/output for local development
  - `sse`: Use Server-Sent Events for cloud deployment
- `MCP_SERVER_URL`: The public URL of the server (default: mcp://127.0.0.1:9000)
  - Used for OAuth2 redirect and server information

The server supports two authentication methods:

1. **Auth Token**: Authenticate using a Synapse authentication token
2. **OAuth2**: Authenticate using Synapse's OAuth2 server
   - Requires registering an OAuth2 client in Synapse (https://www.synapse.org/#!PersonalAccessTokens:OAuth)

## API Endpoints

### Server Information

- `GET /info` - Get server information

### Tools

- `GET /tools` - List available tools
- `POST /tools/authenticate` - Authenticate with Synapse
- `POST /tools/get_oauth_url` - Get the OAuth2 authorization URL
- `POST /tools/get_entity` - Get an entity by ID or name
- `POST /tools/get_entity_annotations` - Get annotations for an entity
- `POST /tools/get_entity_children` - Get child entities of a container entity
- `POST /tools/query_entities` - Query entities based on various criteria
- `POST /tools/query_table` - Query a Synapse table

### Resources

- `GET /resources` - List available resources
- `GET /resources/entity/{id}` - Get entity by ID
- `GET /resources/entity/{id}/annotations` - Get entity annotations
- `GET /resources/entity/{id}/children` - Get entity children
- `GET /resources/query/entities/{entity_type}` - Query entities by type
- `GET /resources/query/entities/parent/{parent_id}` - Query entities by parent ID
- `GET /resources/query/entities/name/{name}` - Query entities by name
- `GET /resources/query/table/{id}/{query}` - Query a table with SQL-like syntax

### OAuth2 Endpoints

- `GET /oauth/login` - Redirect to Synapse OAuth2 login page
- `GET /oauth/callback` - Handle OAuth2 callback from Synapse


## Examples

### Authentication

You need to authenticate with real Synapse credentials to use the server:

```python
import requests

# Authenticate with Synapse
response = requests.post("http://127.0.0.1:9000/tools/authenticate", json={
    "email": "your-synapse-email@example.com",
    "password": "your-synapse-password"
})
result = response.json()
print(result)

# Alternatively, you can authenticate with an API key
response = requests.post("http://127.0.0.1:9000/tools/authenticate", json={
    "api_key": "your-synapse-api-key"
})
```

### OAuth2 Authentication

#### 1. Redirect Flow (Browser-based)

Direct users to the OAuth login URL:
```
http://127.0.0.1:9000/oauth/login?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI
```

#### 2. API-based Flow

For programmatic use, first get the authorization URL:

```python
import requests

# Get OAuth2 authorization URL
response = requests.post("http://127.0.0.1:9000/tools/get_oauth_url", json={
    "client_id": "YOUR_CLIENT_ID",
    "redirect_uri": "YOUR_REDIRECT_URI"
})
auth_url = response.json()["auth_url"]
# Redirect user to auth_url
```


### Getting an Entity

```python
import requests

# Get an entity by ID
response = requests.get("http://127.0.0.1:9000/resources/entity/syn123456")  # Replace with a real Synapse ID
entity = response.json()
print(entity)
```

### Getting Entity Annotations

```python
import requests

# Get annotations for an entity
response = requests.get("http://127.0.0.1:9000/resources/entity/syn123456/annotations")  # Replace with a real Synapse ID
annotations = response.json()
print(annotations)
```

### Querying Entities

```python
import requests

# Query for files in a project
response = requests.get("http://127.0.0.1:9000/resources/query/entities/parent/syn123456", params={  # Replace with a real Synapse ID
    "entity_type": "file"
})
files = response.json()
print(files)
```

### Querying a Table

```python
import requests

# Query a table
table_id = "syn123456"  # Replace with a real Synapse table ID
query = "SELECT * FROM syn123456 LIMIT 10"  # Replace with a real Synapse table ID
response = requests.get(f"http://127.0.0.1:9000/resources/query/table/{table_id}/{query}")
table_data = response.json()
print(table_data)
```

### Getting Datasets in Croissant Format

```python
import requests
import json

# Get public datasets in Croissant format
response = requests.get("http://127.0.0.1:9000/resources/croissant/datasets")
croissant_data = response.json()

# Save to file
with open("croissant_metadata.json", "w") as f:
    json.dump(croissant_data, f, indent=2)
```

## Deployment

### Docker

You can build and run the server using Docker:

```bash
# Build the Docker image
docker build -t synapse-mcp .

# Run the container
docker run -p 9000:9000 -e SYNAPSE_OAUTH_CLIENT_ID=your_client_id -e SYNAPSE_OAUTH_CLIENT_SECRET=your_client_secret -e SYNAPSE_OAUTH_REDIRECT_URI=your_redirect_uri synapse-mcp
docker run -p 9000:9000 -e MCP_TRANSPORT=sse -e MCP_SERVER_URL=mcp://your-domain:9000 synapse-mcp
```

### Fly.io

Deploy to fly.io:

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login to fly.io
flyctl auth login

# Launch the app
flyctl launch

# Set OAuth2 secrets
flyctl secrets set SYNAPSE_OAUTH_CLIENT_ID=your_client_id
flyctl secrets set SYNAPSE_OAUTH_CLIENT_SECRET=your_client_secret
flyctl secrets set SYNAPSE_OAUTH_REDIRECT_URI=https://your-app-name.fly.dev/oauth/callback
flyctl secrets set MCP_TRANSPORT=sse
flyctl secrets set MCP_SERVER_URL=mcp://your-app-name.fly.dev:9000

# Deploy
flyctl deploy
```

### Integrating with Claude Desktop

You can integrate this Synapse MCP server with Claude Desktop to enable Claude to access and work with Synapse data directly in your conversations.

### Setup Instructions

1. First, clone the repository and install the requirements:

```bash
# Clone the repository
git clone https://github.com/susheel/synapse-mcp.git
cd synapse-mcp

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

2. Configure Claude Desktop to use the Synapse MCP server:

   - Open Claude Desktop
   - Click on the Claude menu and select "Settings..."
   - Click on "Developer" in the left-hand bar
   - Click on "Edit Config"
   - Add the following configuration to the `mcpServers` section:

```json
"synapse-mcp": {
  "command": "python",
  "args": [
    "/path/to/synapse-mcp/server.py",
    "--host", "127.0.0.1",
    "--port", "9000"
  ]
}
```

3. Save the configuration file and restart Claude Desktop

4. You can now use Synapse data in your conversations with Claude. For example:
   - "Get the entity with ID syn123456 from Synapse"
   - "Query all files in the Synapse project syn123456"
   - "Get annotations for the Synapse entity syn123456"

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT