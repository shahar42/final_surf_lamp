#!/bin/bash

# Start the Render MCP Server
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the server
python3 render_mcp_server.py