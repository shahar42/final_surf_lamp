#!/bin/bash
# Start Surf Lamp Supabase MCP Server with proper virtual environment
cd "$(dirname "$0")"
source ../esurf/bin/activate
# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
exec python3 fastmcp_supabase_server.py