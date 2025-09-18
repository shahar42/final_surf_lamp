#!/bin/bash
# Start Surf Lamp Supabase MCP Server with proper virtual environment
cd "$(dirname "$0")"
source ../myenv/bin/activate
exec python3 fastmcp_supabase_server.py