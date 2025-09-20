#!/bin/bash
# Start Render MCP Server with proper virtual environment
cd "$(dirname "$0")"
source ../myenv/bin/activate
exec python3 main.py