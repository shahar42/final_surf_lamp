#!/usr/bin/env python3
"""
Simple FastMCP test server to check Claude Code connectivity
"""

import sys
import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("test-server")

# Initialize FastMCP server
mcp = FastMCP("test-server")

@mcp.tool()
def test_tool() -> str:
    """A simple test tool that returns a greeting"""
    return "Hello from test MCP server!"

if __name__ == "__main__":
    logger.info("Starting simple test MCP server...")
    mcp.run(transport='stdio')