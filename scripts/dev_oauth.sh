#!/usr/bin/env bash
set -euo pipefail

# Resolve repository root relative to this script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE; add your OAuth secrets before running this script." >&2
  exit 1
fi

# Load environment variables from .env without leaking values
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${SYNAPSE_OAUTH_CLIENT_ID:?SYNAPSE_OAUTH_CLIENT_ID must be defined in .env}"
: "${SYNAPSE_OAUTH_CLIENT_SECRET:?SYNAPSE_OAUTH_CLIENT_SECRET must be defined in .env}"

# Ensure PAT auth is not used when testing OAuth flows
unset SYNAPSE_PAT || true

export MCP_SERVER_URL="${MCP_SERVER_URL:-http://127.0.0.1:9000/mcp}"
export SYNAPSE_OAUTH_REDIRECT_URI="${SYNAPSE_OAUTH_REDIRECT_URI:-http://127.0.0.1:9000/oauth/callback}"

if ! command -v synapse-mcp >/dev/null 2>&1; then
  echo "synapse-mcp CLI not found. Run 'pip install -e .' inside your virtualenv first." >&2
  exit 1
fi

echo "Starting Synapse MCP with OAuth dev settings..."
echo "- MCP_SERVER_URL: $MCP_SERVER_URL"
echo "- SYNAPSE_OAUTH_REDIRECT_URI: $SYNAPSE_OAUTH_REDIRECT_URI"

auth_flags=("--http" "--debug")

exec synapse-mcp "${auth_flags[@]}" "$@"
