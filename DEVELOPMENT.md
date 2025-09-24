# Local Development Guide

This guide provides instructions for setting up and running the Synapse MCP server in a local development environment. The server is built using FastMCP framework and is meant to support both PAT authentication (local server) and OAuth2 (remote server).

## 1. Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/SageBionetworks/synapse-mcp.git
cd synapse-mcp

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

# 3. Install the package in editable mode
pip install --upgrade -e .
```

If you have previously installed the package, it is important to use the `--upgrade` flag to ensure the console script is properly generated.

## 2. Run the Server

### Start server with HTTP transport for web development/testing

Currently, the server default is **stdio transport** for local use. For development, it is better to start server with `--http` flag (transport is streamable-http) and `--debug` to see detailed logs:

```bash
export SYNAPSE_PAT=$SYNAPSE_AUTH_TOKEN
synapse-mcp --http --debug
```

**To also test OAuth2**

This is fully intended for **contributors only** -- typical end users should use PAT authentication for local development. OAuth2 requires registering your own OAuth client with Synapse, which involves administrative steps that end users shouldn't need to do. As a contributor, you can also add new tools, etc. and test with the method above without having to register for a development client.

Again, you must have development [OAuth 2.0 client credentials](https://help.synapse.org/docs/Using-Synapse-as-an-OAuth-Server.2048327904.html) registered with Synapse and set these environment variables. Make sure `SYNAPSE_PAT` is unset, since `SYNAPSE_PAT` check takes precedence.

```bash
# Set these values for your current terminal session
export SYNAPSE_OAUTH_CLIENT_ID=$CLIENT_ID
export SYNAPSE_OAUTH_CLIENT_SECRET=$CLIENT_SECRET
export SYNAPSE_OAUTH_REDIRECT_URI="http://127.0.0.1:9000/oauth/callback"
export MCP_SERVER_URL="http://127.0.0.1:9000/mcp"
synapse-mcp --http --debug
```

### 3. Add to local AI client like Claude Code

```bash
claude mcp add --transport http synapse -- http://127.0.0.1:9000/mcp
```

## Running Tests

To run the test suite, use `pytest`:

```bash
# Run all tests
python -m pytest
```

### Redis session storage smoke test

If you have a live Redis instance available, run the smoke test to validate connectivity and TTL behaviour:

```bash
export REDIS_URL="redis://localhost:6379/0"
python scripts/smoke_redis_session_storage.py
```

The script exercises token creation, replacement, expiration, and cleanup. It exits non-zero if anything fails.

## Deployment 

### Docker build and run

```bash
# Build the Docker image
docker build -t synapse-mcp .

# Run the container with PAT
docker run -p 9000:9000 \
  -e SYNAPSE_PAT="your_token_here" \
  synapse-mcp

# OR run with OAuth
docker run -p 9000:9000 \
  -e SYNAPSE_OAUTH_CLIENT_ID=$SYNAPSE_OAUTH_CLIENT_ID \
  -e SYNAPSE_OAUTH_CLIENT_SECRET=$SYNAPSE_OAUTH_CLIENT_SECRET \
  -e SYNAPSE_OAUTH_REDIRECT_URI="http://127.0.0.1:9000/oauth/callback" \
  -e MCP_SERVER_URL="http://127.0.0.1:9000/mcp" \
  -e MCP_TRANSPORT="streamable-http" \
  synapse-mcp
```

### Fly.io

> [!WARNING]
> These are placeholder deployment info and actual production deployment may change.

The project is configured for easy deployment to [Fly.io](https://fly.io), a platform for running full-stack apps and databases close to your users.

#### Prerequisites

1.  **Create a Fly.io Account**: If you don't have one, sign up at [fly.io](https://fly.io).
2.  **Install `flyctl`**: This is the command-line tool for managing Fly.io apps. Follow the installation instructions for your operating system at [fly.io/docs/hands-on/install-flyctl](https://fly.io/docs/hands-on/install-flyctl/).

#### Deployment Steps

1.  **Log in to Fly.io**:

    Open your terminal and run:
    ```bash
    flyctl auth login
    ```
    This will open a browser window to authenticate your `flyctl` client.

2.  **Launch the App**:

    The `flyctl launch` command detects the `fly.toml` file, builds a new application, and deploys it. It will ask you to choose an app name (defaults to `synapse-mcp`) and a region.

    ```bash
    flyctl launch
    ```

3.  **Set OAuth2 Secrets**:

    For the server to authenticate with Synapse via OAuth2 using FastMCP's OAuth proxy, provide it with a client ID, a client secret, and the correct redirect URI.

    Run the following commands, replacing the placeholder values with your actual credentials:
    ```bash
    flyctl secrets set SYNAPSE_OAUTH_CLIENT_ID="your_client_id"
    flyctl secrets set SYNAPSE_OAUTH_CLIENT_SECRET="your_client_secret"
    flyctl secrets set SYNAPSE_OAUTH_REDIRECT_URI="https://your-app-name.fly.dev/oauth/callback"
    flyctl secrets set REDIS_URL="redis://:password@your-redis-host:6379/0"
    ```
    *Note: The `fly.toml` already sets `MCP_TRANSPORT=streamable-http` and `MCP_SERVER_URL` as environment variables, so you don't need to set them as secrets.*

4.  **Deploy Your Application**:

    After setting the secrets, you can deploy the application.
    ```bash
    flyctl deploy
    ```
    This command uploads your code, builds it into a Docker image on Fly.io's builders, and deploys it to the platform.

5.  **Check the Status**:

    Once the deployment is complete, you can check the status of your app:
    ```bash
    flyctl status
    ```

Your Synapse MCP server is now live on Fly.io. You can access it at `https://your-app-name.fly.dev`.
