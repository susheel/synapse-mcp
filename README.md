# Synapse MCP Server

A Model Context Protocol (MCP) server that exposes Synapse Entities (Datasets, Projects, Folders, Files, Tables) with their annotations.

## Overview

This server provides a RESTful API for accessing Synapse entities and their annotations through the Model Context Protocol (MCP). It allows you to:

- Authenticate with Synapse
- Retrieve entities by ID
- Get entity annotations
- Get entity children
- Query entities based on various criteria
- Query Synapse tables

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
python server.py
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

Run the Synapse MCP server

options:
  -h, --help     show this help message and exit
  --host HOST    Host to bind to
  --port PORT    Port to listen on
  --debug        Enable debug logging
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

## API Endpoints

### Server Information

- `GET /info` - Get server information

### Tools

- `GET /tools` - List available tools
- `POST /tools/authenticate` - Authenticate with Synapse
- `POST /tools/get_entity` - Get an entity by ID
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

## License

MIT