# Local Development Guide

This guide provides instructions for setting up and running the Synapse MCP server in a local development environment, including how to test the OAuth2 authentication flow.

## Local Development Setup

To set up the server for local development, espcially to contribute to the project, follow these steps to install in editable mode.

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

This command uses the `-e` flag to install the package in "editable" mode, meaning any changes you make to the source code will be immediately effective. If you have previously installed the package, it is important to use the `--upgrade` flag to ensure the console script is properly generated.

## Running the Server Locally

### Without Authentication

With local MCP servers, authentication can be optional. 
You can search for data and retrieve certain resources on Synapse without providing Synapse account credentials. 

Run the server using the `synapse-mcp` command. 
For development, it is highly recommended to run the server in debug mode to see logs. 

```bash
synapse-mcp --host 127.0.0.1 --port 9000 --debug
```

### With Authentication

#### Method 1: Authentication with Personal Auth Token

Just make sure server is started with Synapse Personal Access Token.
```bash
export SYNAPSE_PAT="YOUR_TOKEN_HERE"
synapse-mcp --host 127.0.0.1 --port 9000 --debug
```

#### Method 2: Authentication with OAuth2

This is more advanced and fully intended for contributors. 
To run and test the full OAuth2 flow with your local server, you **must** have development [OAuth 2.0 client credentials](https://help.synapse.org/docs/Using-Synapse-as-an-OAuth-Server.2048327904.html) and supply them to the application as environment variables. 
This is the same method used for the deployed remote server. 

Before starting the server, run the following commands in your terminal, replacing the placeholders with the actual values from the file:

```bash
# Set these values for your current terminal session
export SYNAPSE_OAUTH_CLIENT_ID="your_dev_client_id"
export SYNAPSE_OAUTH_CLIENT_SECRET="your_dev_client_secret"
export SYNAPSE_OAUTH_REDIRECT_URI="http://127.0.0.1:9000/oauth/callback"
synapse-mcp --host 127.0.0.1 --port 9000 --debug
```

## Running Tests

To run the test suite, use `pytest`:

```bash
# Run all tests
python -m pytest
```

## Deployment 

### Docker

Build and run the server using Docker.

```bash
# Build the Docker image
docker build -t synapse-mcp .

# Run the container
docker run -p 9000:9000 -e SYNAPSE_OAUTH_CLIENT_ID=your_client_id -e SYNAPSE_OAUTH_CLIENT_SECRET=your_client_secret -e SYNAPSE_OAUTH_REDIRECT_URI=your_redirect_uri synapse-mcp
docker run -p 9000:9000 -e MCP_TRANSPORT=sse -e MCP_SERVER_URL=mcp://your-domain:9000 synapse-mcp
```

### Fly.io

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

    The `flyctl launch` command detects the `fly.toml` file, builds a new application, and deploys it. It will ask you to choose an app name (defaults to `synapse-research-mcp`) and a region.

    ```bash
    flyctl launch
    ```

3.  **Set OAuth2 Secrets**:

    For the server to authenticate with Synapse via OAuth2, provide it with a client ID, a client secret, and the correct redirect URI.

    Run the following commands, replacing the placeholder values with your actual credentials:
    ```bash
    flyctl secrets set SYNAPSE_OAUTH_CLIENT_ID="your_client_id"
    flyctl secrets set SYNAPSE_OAUTH_CLIENT_SECRET="your_client_secret"
    flyctl secrets set SYNAPSE_OAUTH_REDIRECT_URI="https://your-app-name.fly.dev/oauth/callback"
    ```
    *Note: The `fly.toml` already sets `MCP_TRANSPORT` and `MCP_SERVER_URL` as environment variables, so you don't need to set them as secrets.*

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

