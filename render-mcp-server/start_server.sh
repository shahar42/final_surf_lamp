#!/bin/bash

# Start the Render MCP Server
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment (relative path)
source ../esurf/bin/activate

# Run the server
exec python3 render_mcp_server.py