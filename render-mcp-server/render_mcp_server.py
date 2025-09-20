#!/usr/bin/env python3
"""
Render MCP Server using FastMCP and curl
Provides access to Render service logs, deployments, and status with curl-based API calls.
"""

import os
import sys
import asyncio
import subprocess
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

# MCP imports
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("render-mcp")

# Initialize FastMCP server
mcp = FastMCP("render")

# Configuration
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s")
SERVICE_ID = os.getenv("SERVICE_ID", "srv-d2chm8mr433s73anlc0g")
RENDER_BASE_URL = "https://api.render.com"

async def run_curl(url: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Run curl command and return parsed JSON response"""

    cmd = ["curl", "-s", "-w", "%{http_code}"]

    # Add headers
    cmd.extend(["-H", f"Authorization: Bearer {RENDER_API_KEY}"])
    cmd.extend(["-H", "Content-Type: application/json"])
    cmd.extend(["-H", "User-Agent: Render-MCP-Server/1.0"])

    # Add method
    if method != "GET":
        cmd.extend(["-X", method])

    # Add JSON data for POST requests
    if data:
        cmd.extend(["-d", json.dumps(data)])

    cmd.append(url)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Curl failed: {stderr.decode()}")

        output = stdout.decode()

        # Split response body and status code
        if len(output) < 3:
            raise Exception("Invalid curl response")

        status_code = int(output[-3:])
        response_body = output[:-3]

        # Handle HTTP errors
        if status_code >= 400:
            raise Exception(f"HTTP {status_code}: {response_body}")

        # Parse JSON response
        if response_body.strip():
            return json.loads(response_body)
        else:
            return {}

    except Exception as e:
        raise Exception(f"API call failed: {str(e)}")




@mcp.tool()
async def render_deployments(service_id: Optional[str] = None, limit: int = 10) -> str:
    """
    Get recent deployment history for the surf lamp service.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        limit: Number of recent deployments to show (max 50)

    Returns:
        Formatted deployment history
    """
    try:
        target_service_id = service_id or SERVICE_ID
        limit = min(limit, 50)

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/deploys?limit={limit}"
        response = await run_curl(url)

        deployments = response if isinstance(response, list) else response.get('deploys', [])

        if not deployments:
            return f"No deployments found for service {target_service_id}"

        # Format deployment history
        formatted = []
        formatted.append(f"🚀 Recent Deployments for Service: {target_service_id}")
        formatted.append(f"📊 Showing {len(deployments)} most recent deployments")
        formatted.append("\n" + "="*80 + "\n")

        for i, deploy in enumerate(deployments, 1):
            deploy_id = deploy.get('id', 'Unknown')
            status = deploy.get('status', 'Unknown')
            created_at = deploy.get('createdAt', 'Unknown')
            finished_at = deploy.get('finishedAt', 'In Progress')

            # Status emoji
            status_emoji = {
                'live': '✅',
                'build_failed': '❌',
                'build_in_progress': '🔄',
                'canceled': '⏹️',
                'pre_deploy_failed': '⚠️'
            }.get(status, '❓')

            formatted.append(f"[{i:02d}] {status_emoji} Deploy {deploy_id}")
            formatted.append(f"     Status: {status}")
            formatted.append(f"     Created: {created_at}")
            formatted.append(f"     Finished: {finished_at}")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching deployments: {str(e)}"

@mcp.tool()
async def render_service_status(service_id: Optional[str] = None) -> str:
    """
    Get current service status and health information.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Current service status and details
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}"
        response = await run_curl(url)

        # Extract key information
        name = response.get('name', 'Unknown')
        service_type = response.get('type', 'Unknown')
        created_at = response.get('createdAt', 'Unknown')
        updated_at = response.get('updatedAt', 'Unknown')

        # Service type specific info
        service_details = response.get('serviceDetails', {})
        if service_type == 'web_service':
            url_info = service_details.get('url', 'No URL')
        else:
            url_info = 'N/A (Background Service)'

        formatted = []
        formatted.append(f"📊 Service Status: {target_service_id}")
        formatted.append(f"✅ {name}")
        formatted.append("\n" + "="*50)
        formatted.append(f"Type: {service_type}")
        formatted.append(f"URL: {url_info}")
        formatted.append(f"Created: {created_at}")
        formatted.append(f"Last Updated: {updated_at}")

        # Add runtime info if available
        if service_details:
            if 'numInstances' in service_details:
                formatted.append(f"Instances: {service_details['numInstances']}")
            if 'plan' in service_details:
                formatted.append(f"Plan: {service_details['plan']}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching service status: {str(e)}"


@mcp.tool()
async def render_service_events(service_id: Optional[str] = None, limit: int = 20) -> str:
    """
    Get recent service events including builds, deploys, and health changes.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        limit: Number of recent events to show (max 50)

    Returns:
        Formatted service events timeline
    """
    try:
        target_service_id = service_id or SERVICE_ID
        limit = min(limit, 50)

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/events?limit={limit}"
        response = await run_curl(url)

        events = response if isinstance(response, list) else response.get('events', [])

        if not events:
            return f"No events found for service {target_service_id}"

        # Format events timeline
        formatted = []
        formatted.append(f"📅 Service Events Timeline: {target_service_id}")
        formatted.append(f"📊 Showing {len(events)} most recent events")
        formatted.append("\n" + "="*80 + "\n")

        for i, event_data in enumerate(events, 1):
            event = event_data.get('event', {})
            event_type = event.get('type', 'Unknown')
            timestamp = event.get('timestamp', 'Unknown')
            details = event.get('details', {})

            # Event type emoji
            type_emoji = {
                'deploy_started': '🚀',
                'deploy_ended': '✅',
                'build_started': '🔨',
                'build_ended': '🏗️',
                'server_unhealthy': '⚠️',
                'server_healthy': '💚'
            }.get(event_type, '📋')

            formatted.append(f"[{i:02d}] {type_emoji} {event_type}")
            formatted.append(f"     Time: {timestamp}")

            # Add specific details based on event type
            if 'deployId' in details:
                formatted.append(f"     Deploy ID: {details['deployId']}")
            if 'buildId' in details:
                formatted.append(f"     Build ID: {details['buildId']}")
            if 'deployStatus' in details:
                formatted.append(f"     Status: {details['deployStatus']}")
            if 'buildStatus' in details:
                formatted.append(f"     Status: {details['buildStatus']}")
            if 'instanceID' in details:
                formatted.append(f"     Instance: {details['instanceID']}")

            # Add trigger info if available
            trigger = details.get('trigger', {})
            if trigger.get('newCommit'):
                commit = trigger['newCommit'][:8]
                formatted.append(f"     Commit: {commit}")
            if trigger.get('manual'):
                formatted.append(f"     Trigger: Manual deployment")

            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching service events: {str(e)}"

@mcp.tool()
async def render_environment_vars(service_id: Optional[str] = None) -> str:
    """
    Get environment variables configured for the service.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Formatted environment variables (values partially masked for security)
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/env-vars"
        response = await run_curl(url)

        env_vars = response if isinstance(response, list) else response.get('envVars', [])

        if not env_vars:
            return f"No environment variables found for service {target_service_id}"

        # Format environment variables
        formatted = []
        formatted.append(f"🔧 Environment Variables: {target_service_id}")
        formatted.append(f"📊 Found {len(env_vars)} environment variables")
        formatted.append("\n" + "="*60 + "\n")

        for i, env_data in enumerate(env_vars, 1):
            env_var = env_data.get('envVar', {})
            key = env_var.get('key', 'Unknown')
            value = env_var.get('value', '')

            # Mask sensitive values
            if len(value) > 20:
                masked_value = value[:8] + "***" + value[-4:]
            elif len(value) > 8:
                masked_value = value[:4] + "***"
            else:
                masked_value = "***"

            # Don't mask certain common values
            if key in ['PYTHON_VERSION'] or value in ['3.12.3']:
                masked_value = value

            formatted.append(f"[{i:02d}] {key} = {masked_value}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching environment variables: {str(e)}"

@mcp.tool()
async def render_list_all_services() -> str:
    """
    List all services in the Render account.

    Returns:
        Formatted list of all services with basic info
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/services"
        response = await run_curl(url)

        services = response if isinstance(response, list) else response.get('services', [])

        if not services:
            return "No services found in this Render account"

        # Format services list
        formatted = []
        formatted.append(f"🏢 All Render Services")
        formatted.append(f"📊 Found {len(services)} services")
        formatted.append("\n" + "="*80 + "\n")

        for i, service_data in enumerate(services, 1):
            service = service_data.get('service', {})
            service_id = service.get('id', 'Unknown')
            name = service.get('name', 'Unknown')
            service_type = service.get('type', 'Unknown')
            created_at = service.get('createdAt', 'Unknown')

            # Service type emoji
            type_emoji = {
                'web_service': '🌐',
                'background_worker': '⚙️',
                'private_service': '🔒',
                'static_site': '📄'
            }.get(service_type, '📋')

            formatted.append(f"[{i:02d}] {type_emoji} {name}")
            formatted.append(f"     ID: {service_id}")
            formatted.append(f"     Type: {service_type}")
            formatted.append(f"     Created: {created_at}")

            # Add URL for web services
            service_details = service.get('serviceDetails', {})
            if service_type == 'web_service' and 'url' in service_details:
                formatted.append(f"     URL: {service_details['url']}")

            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error listing services: {str(e)}"

@mcp.tool()
async def render_deploy_details(deploy_id: str, service_id: Optional[str] = None) -> str:
    """
    Get detailed information about a specific deployment.

    Args:
        deploy_id: The deployment ID to get details for
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Detailed deployment information including commit details
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/deploys/{deploy_id}"
        response = await run_curl(url)

        deploy = response.get('deploy', response)

        if not deploy:
            return f"Deployment {deploy_id} not found"

        # Format deployment details
        formatted = []
        formatted.append(f"🚀 Deployment Details: {deploy_id}")
        formatted.append("\n" + "="*60 + "\n")

        # Basic info
        formatted.append(f"Service ID: {target_service_id}")
        formatted.append(f"Status: {deploy.get('status', 'Unknown')}")
        formatted.append(f"Trigger: {deploy.get('trigger', 'Unknown')}")
        formatted.append(f"Created: {deploy.get('createdAt', 'Unknown')}")
        formatted.append(f"Started: {deploy.get('startedAt', 'Unknown')}")
        formatted.append(f"Finished: {deploy.get('finishedAt', 'In Progress')}")

        # Commit info
        commit = deploy.get('commit', {})
        if commit:
            formatted.append("\n📝 Commit Information:")
            formatted.append(f"Hash: {commit.get('id', 'Unknown')}")
            formatted.append(f"Message: {commit.get('message', 'No message')}")
            formatted.append(f"Created: {commit.get('createdAt', 'Unknown')}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching deployment details: {str(e)}"

# Test API connection on startup
async def test_connection():
    """Test Render API connection on startup"""
    try:
        await render_service_status()
        logger.info("✅ Render API connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Render API connection failed: {e}")
        return False

logger.info("Render MCP Server initialized with FastMCP")

if __name__ == "__main__":
    # Test API connection
    asyncio.run(test_connection())

    # Run the FastMCP server
    logger.info("Starting Render MCP Server for Claude Code...")
    logger.info("MCP Server ready for Claude Code with FastMCP integration")
    mcp.run(transport='stdio')