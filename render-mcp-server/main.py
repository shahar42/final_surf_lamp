"""Render MCP Server - Real-time access to Render logs, deployments, and metrics"""

import logging
import sys
from mcp.server.fastmcp import FastMCP
from config import settings

# Import all tools
from tools.logs import get_render_logs, search_logs, get_recent_errors
from tools.deployments import get_deployments, get_service_status, get_latest_deployment_logs
from tools.metrics import get_service_metrics, get_performance_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("render-mcp-server")

# Initialize FastMCP server
mcp = FastMCP("render-mcp-server")

# Register all tools with the MCP server
@mcp.tool()
async def render_logs(
    service_id: str = None,
    start_time: str = None,
    end_time: str = None,
    limit: int = 50,
    search_text: str = None
) -> str:
    """
    Fetch logs from Render for the surf lamp service with optional filtering.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        start_time: Start time in ISO format (e.g. '2025-01-20T10:00:00Z')
        end_time: End time in ISO format
        limit: Maximum number of logs to return (max 1000)
        search_text: Filter logs containing this text

    Returns:
        Formatted logs suitable for debugging
    """
    return await get_render_logs(service_id, start_time, end_time, limit, search_text)


@mcp.tool()
async def search_render_logs(
    search_text: str,
    hours_back: int = 2,
    service_id: str = None
) -> str:
    """
    Search recent logs for specific text patterns.

    Args:
        search_text: Text to search for in log messages
        hours_back: How many hours back to search (default: 2)
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Matching logs with context
    """
    return await search_logs(search_text, hours_back, service_id)


@mcp.tool()
async def render_recent_errors(
    hours_back: int = 6,
    service_id: str = None
) -> str:
    """
    Get recent error and warning logs.

    Args:
        hours_back: How many hours back to search (default: 6)
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Recent error logs
    """
    return await get_recent_errors(hours_back, service_id)


@mcp.tool()
async def render_deployments(
    service_id: str = None,
    limit: int = 10
) -> str:
    """
    Get recent deployment history for the surf lamp service.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        limit: Number of recent deployments to show (max 50)

    Returns:
        Formatted deployment history
    """
    return await get_deployments(service_id, limit)


@mcp.tool()
async def render_service_status(
    service_id: str = None
) -> str:
    """
    Get current service status and health information.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Current service status and details
    """
    return await get_service_status(service_id)


@mcp.tool()
async def render_latest_deployment_logs(
    service_id: str = None
) -> str:
    """
    Get logs from the most recent deployment.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Logs from the latest deployment
    """
    return await get_latest_deployment_logs(service_id)


@mcp.tool()
async def render_metrics(
    service_id: str = None,
    hours_back: int = 2
) -> str:
    """
    Get service performance metrics (CPU, memory, requests).

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        hours_back: How many hours of metrics to retrieve (default: 2)

    Returns:
        Formatted service metrics
    """
    return await get_service_metrics(service_id, hours_back)


@mcp.tool()
async def render_health_check(
    service_id: str = None
) -> str:
    """
    Get a comprehensive health check combining status, recent deployments, and performance metrics.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Complete health summary
    """
    return await get_performance_summary(service_id)


# No persistent session management needed - using stateless pattern


async def test_connection():
    """Test Render API connection on startup"""
    try:
        # Create a temporary session just for testing
        import aiohttp
        from config import settings

        timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
        headers = {
            "Authorization": f"Bearer {settings.RENDER_API_KEY}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession(
            base_url=settings.RENDER_BASE_URL,
            headers=headers,
            timeout=timeout
        ) as session:
            async with session.get(f"services/{settings.SERVICE_ID}") as response:
                if response.status == 200:
                    logger.info("✅ Render API connection successful")
                    return True
                else:
                    logger.error(f"❌ Render API returned status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Render API connection failed: {e}")
        return False

logger.info("🎯 Render MCP Server for Surf Lamp debugging")
logger.info("📋 Available tools:")
logger.info("   - render_logs: Fetch filtered logs")
logger.info("   - search_render_logs: Search for specific text")
logger.info("   - render_recent_errors: Find recent errors")
logger.info("   - render_deployments: Deployment history")
logger.info("   - render_service_status: Current service status")
logger.info("   - render_latest_deployment_logs: Latest deployment logs")
logger.info("   - render_metrics: Performance metrics")
logger.info("   - render_health_check: Complete health summary")

if __name__ == "__main__":
    import asyncio
    # Test API connection
    if asyncio.run(test_connection()):
        logger.info("Starting Render MCP Server for Claude Code...")
        logger.info("MCP Server ready for Claude Code with FastMCP integration")
        mcp.run(transport='stdio')
    else:
        logger.error("Failed to connect to Render API - exiting")
        sys.exit(1)