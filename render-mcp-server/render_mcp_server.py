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
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("SERVICE_ID", "srv-d2chm8mr433s73anlc0g")
OWNER_ID = os.getenv("OWNER_ID")
BACKGROUND_SERVICE_ID = os.getenv("BACKGROUND_SERVICE_ID")

if not RENDER_API_KEY:
    logger.error("❌ RENDER_API_KEY environment variable is required")
    sys.exit(1)
if not OWNER_ID:
    logger.error("❌ OWNER_ID environment variable is required for log access")
    sys.exit(1)
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
        Formatted deployment history (all timestamps in UTC - add 3 hours for Israel time)
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
        Current service status and details (timestamps in UTC - add 3 hours for Israel time)
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
        Formatted service events timeline (all timestamps in UTC - add 3 hours for Israel time)
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

# =================== NEW ENHANCED TOOLS ===================

# Core data fetcher for complex endpoints
async def _fetch_all_services_data() -> Dict[str, Any]:
    """Private function to fetch and parse all services data"""
    url = f"{RENDER_BASE_URL}/v1/services?limit=50"
    response = await run_curl(url)
    return response

def _parse_service_data(services_response):
    """Extract and structure key information from services"""
    parsed_services = []
    services_list = services_response if isinstance(services_response, list) else []

    for item in services_list:
        service = item.get('service', {})
        service_details = service.get('serviceDetails', {})
        plan = service_details.get('plan', 'unknown')

        # Calculate monthly cost
        cost = 0
        if plan == 'starter':
            cost = 7.0
        elif plan == 'standard':
            cost = 25.0
        elif plan == 'pro':
            cost = 85.0
        # free = $0

        parsed_services.append({
            'id': service.get('id'),
            'name': service.get('name'),
            'type': service.get('type'),
            'plan': plan,
            'cost': cost,
            'suspended': service.get('suspended'),
            'ssh_address': service_details.get('sshAddress'),
            'url': service_details.get('url'),
            'auto_deploy': service.get('autoDeploy'),
            'branch': service.get('branch'),
            'last_updated': service.get('updatedAt'),
            'region': service_details.get('region'),
            'num_instances': service_details.get('numInstances', 1),
            'build_command': service_details.get('envSpecificDetails', {}).get('buildCommand'),
            'start_command': service_details.get('envSpecificDetails', {}).get('startCommand')
        })
    return parsed_services

def _format_service_list(services, detailed=False):
    """Format services for display"""
    formatted = []
    for service in services:
        status_emoji = "✅" if service['suspended'] == 'not_suspended' else "⏸️"
        type_emoji = {
            'web_service': '🌐',
            'background_worker': '⚙️',
            'private_service': '🔒',
            'static_site': '📄'
        }.get(service['type'], '📋')

        cost_str = f"${service['cost']:.0f}/mo" if service['cost'] > 0 else "FREE"

        line = f"{status_emoji} {type_emoji} {service['name']} ({service['plan']}, {cost_str})"

        if detailed:
            line += f"\n     ID: {service['id']}"
            if service['url']:
                line += f"\n     URL: {service['url']}"
            if service['ssh_address']:
                line += f"\n     SSH: {service['ssh_address']}"
            line += f"\n     Region: {service['region']}, Instances: {service['num_instances']}"
            line += f"\n     Auto-deploy: {service['auto_deploy']} (branch: {service['branch']})"

        formatted.append(line)

    return "\n".join(formatted)

@mcp.tool()
async def render_services_overview() -> str:
    """
    📊 Quick overview of all Render services with cost and status summary.

    Returns:
        High-level dashboard of all services including costs and status
    """
    try:
        data = await _fetch_all_services_data()
        services = _parse_service_data(data)

        if not services:
            return "No services found in this Render account"

        # Calculate summary stats
        total_services = len(services)
        active_services = len([s for s in services if s['suspended'] == 'not_suspended'])
        suspended_services = total_services - active_services
        total_cost = sum(s['cost'] for s in services)

        # Group by type
        web_services = len([s for s in services if s['type'] == 'web_service'])
        workers = len([s for s in services if s['type'] == 'background_worker'])

        formatted = []
        formatted.append("🏢 Render Services Overview")
        formatted.append("═" * 40)
        formatted.append(f"📊 Total Services: {total_services}")
        formatted.append(f"✅ Active: {active_services}")
        if suspended_services > 0:
            formatted.append(f"⏸️ Suspended: {suspended_services}")
        formatted.append(f"💰 Monthly Cost: ${total_cost:.2f}")
        formatted.append(f"🌐 Web Services: {web_services}")
        formatted.append(f"⚙️ Workers: {workers}")
        formatted.append("\n" + "─" * 40)
        formatted.append(_format_service_list(services))

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching services overview: {str(e)}"

@mcp.tool()
async def render_services_detailed(service_filter: str = "all") -> str:
    """
    🔍 Detailed view of services with filtering options.

    Args:
        service_filter: Filter services - "all", "web", "worker", "active", "suspended", "paid", "free"

    Returns:
        Detailed information about filtered services
    """
    try:
        data = await _fetch_all_services_data()
        services = _parse_service_data(data)

        # Apply filters
        if service_filter == "web":
            services = [s for s in services if s['type'] == 'web_service']
        elif service_filter == "worker":
            services = [s for s in services if s['type'] == 'background_worker']
        elif service_filter == "active":
            services = [s for s in services if s['suspended'] == 'not_suspended']
        elif service_filter == "suspended":
            services = [s for s in services if s['suspended'] != 'not_suspended']
        elif service_filter == "paid":
            services = [s for s in services if s['cost'] > 0]
        elif service_filter == "free":
            services = [s for s in services if s['cost'] == 0]

        if not services:
            return f"No services found matching filter: {service_filter}"

        formatted = []
        formatted.append(f"🔍 Detailed Services View ({service_filter})")
        formatted.append("═" * 60)
        formatted.append(f"📊 Showing {len(services)} services")
        formatted.append("\n" + "─" * 60 + "\n")
        formatted.append(_format_service_list(services, detailed=True))

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching detailed services: {str(e)}"

@mcp.tool()
async def render_services_cost_analysis() -> str:
    """
    💰 Analyze costs across all services with optimization suggestions.

    Returns:
        Cost breakdown and optimization recommendations
    """
    try:
        data = await _fetch_all_services_data()
        services = _parse_service_data(data)

        if not services:
            return "No services found for cost analysis"

        # Cost analysis
        total_cost = sum(s['cost'] for s in services)
        paid_services = [s for s in services if s['cost'] > 0]
        free_services = [s for s in services if s['cost'] == 0]
        suspended_paid = [s for s in paid_services if s['suspended'] != 'not_suspended']

        formatted = []
        formatted.append("💰 Cost Analysis Report")
        formatted.append("═" * 40)
        formatted.append(f"💸 Total Monthly Cost: ${total_cost:.2f}")
        formatted.append(f"💳 Paid Services: {len(paid_services)}")
        formatted.append(f"🆓 Free Services: {len(free_services)}")

        if suspended_paid:
            wasted_cost = sum(s['cost'] for s in suspended_paid)
            formatted.append(f"⚠️ Suspended Paid Services: ${wasted_cost:.2f}/mo wasted")

        formatted.append("\n📊 Cost Breakdown:")
        for service in paid_services:
            status = "⏸️ SUSPENDED" if service['suspended'] != 'not_suspended' else "✅ Active"
            formatted.append(f"   ${service['cost']:.0f}/mo - {service['name']} ({status})")

        # Optimization suggestions
        if suspended_paid:
            formatted.append("\n💡 Optimization Suggestions:")
            formatted.append("   • Consider deleting suspended paid services")
            for service in suspended_paid:
                formatted.append(f"     - {service['name']}: ${service['cost']:.0f}/mo savings")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error analyzing costs: {str(e)}"

@mcp.tool()
async def render_services_ssh_info() -> str:
    """
    🔗 Get SSH connection details for all services.

    Returns:
        SSH addresses for direct server access and debugging
    """
    try:
        data = await _fetch_all_services_data()
        services = _parse_service_data(data)

        services_with_ssh = [s for s in services if s['ssh_address']]

        if not services_with_ssh:
            return "No services found with SSH access"

        formatted = []
        formatted.append("🔗 SSH Connection Information")
        formatted.append("═" * 50)

        for service in services_with_ssh:
            status = "✅" if service['suspended'] == 'not_suspended' else "⏸️"
            formatted.append(f"{status} {service['name']} ({service['type']})")
            formatted.append(f"   ssh {service['ssh_address']}")
            formatted.append(f"   Region: {service['region']}")
            formatted.append("")

        formatted.append("💡 Usage: Copy the SSH command to connect directly to your service")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching SSH info: {str(e)}"

# Service Management Tools
@mcp.tool()
async def render_restart_service(service_id: Optional[str] = None) -> str:
    """
    🔄 Restart a Render service.

    Args:
        service_id: Service ID to restart (defaults to configured SERVICE_ID)

    Returns:
        Restart operation result
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/restart"
        response = await run_curl(url, method="POST")

        return f"✅ Service restart initiated for {target_service_id}\n🔄 Service will restart momentarily"

    except Exception as e:
        return f"❌ Error restarting service: {str(e)}"

@mcp.tool()
async def render_suspend_service(service_id: Optional[str] = None) -> str:
    """
    ⏸️ Suspend a Render service (stops it from running).

    Args:
        service_id: Service ID to suspend (defaults to configured SERVICE_ID)

    Returns:
        Suspend operation result
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/suspend"
        response = await run_curl(url, method="POST")

        return f"⏸️ Service suspension initiated for {target_service_id}\n💰 Service will stop running and billing will pause"

    except Exception as e:
        return f"❌ Error suspending service: {str(e)}"

@mcp.tool()
async def render_resume_service(service_id: Optional[str] = None) -> str:
    """
    ▶️ Resume a suspended Render service.

    Args:
        service_id: Service ID to resume (defaults to configured SERVICE_ID)

    Returns:
        Resume operation result
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/resume"
        response = await run_curl(url, method="POST")

        return f"▶️ Service resume initiated for {target_service_id}\n🚀 Service will start up shortly (30-60 seconds)"

    except Exception as e:
        return f"❌ Error resuming service: {str(e)}"

@mcp.tool()
async def render_scale_service(num_instances: int, service_id: Optional[str] = None) -> str:
    """
    📊 Scale a Render service to specified number of instances.

    Args:
        num_instances: Number of instances (0 to stop, 1+ to scale up)
        service_id: Service ID to scale (defaults to configured SERVICE_ID)

    Returns:
        Scaling operation result with cost implications
    """
    try:
        target_service_id = service_id or SERVICE_ID

        if num_instances < 0:
            return "❌ Number of instances must be 0 or greater"

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/scale"
        data = {"numInstances": num_instances}
        response = await run_curl(url, method="POST", data=data)

        if num_instances == 0:
            message = f"🛑 Service {target_service_id} scaled to 0 instances\n💰 Service stopped - no charges while scaled to 0"
        elif num_instances == 1:
            message = f"📊 Service {target_service_id} scaled to 1 instance\n💰 Normal billing applies"
        else:
            message = f"📈 Service {target_service_id} scaled to {num_instances} instances\n💰 Higher billing - {num_instances}x instance cost"

        return message

    except Exception as e:
        return f"❌ Error scaling service: {str(e)}"

@mcp.tool()
async def render_get_custom_domains(service_id: Optional[str] = None) -> str:
    """
    🌐 List custom domains configured for a service.

    Args:
        service_id: Service ID to check (defaults to configured SERVICE_ID)

    Returns:
        List of custom domains and their status
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/custom-domains"
        response = await run_curl(url)

        domains = response if isinstance(response, list) else []

        if not domains:
            return f"🌐 No custom domains configured for service {target_service_id}\n💡 Using default .onrender.com domain"

        formatted = []
        formatted.append(f"🌐 Custom Domains for {target_service_id}")
        formatted.append("═" * 50)

        for i, domain in enumerate(domains, 1):
            domain_name = domain.get('name', 'Unknown')
            status = domain.get('verificationStatus', 'Unknown')
            formatted.append(f"[{i:02d}] {domain_name} - {status}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching custom domains: {str(e)}"

@mcp.tool()
async def render_get_secret_files(service_id: Optional[str] = None) -> str:
    """
    📄 List secret files configured for a service.

    Args:
        service_id: Service ID to check (defaults to configured SERVICE_ID)

    Returns:
        List of secret files and their details
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/secret-files"
        response = await run_curl(url)

        files = response if isinstance(response, list) else []

        if not files:
            return f"📄 No secret files configured for service {target_service_id}"

        formatted = []
        formatted.append(f"📄 Secret Files for {target_service_id}")
        formatted.append("═" * 50)

        for i, file_data in enumerate(files, 1):
            file_info = file_data.get('secretFile', {})
            name = file_info.get('name', 'Unknown')
            path = file_info.get('path', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Path: {path}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching secret files: {str(e)}"

@mcp.tool()
async def render_get_service_instances(service_id: Optional[str] = None) -> str:
    """
    🖥️ List running instances for a service.

    Args:
        service_id: Service ID to check (defaults to configured SERVICE_ID)

    Returns:
        List of service instances with creation times and status
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/instances"
        response = await run_curl(url)

        instances = response if isinstance(response, list) else []

        if not instances:
            return f"🖥️ No running instances found for service {target_service_id}"

        formatted = []
        formatted.append(f"🖥️ Service Instances for {target_service_id}")
        formatted.append("═" * 50)

        for i, instance in enumerate(instances, 1):
            instance_id = instance.get('id', 'Unknown')
            created_at = instance.get('createdAt', 'Unknown')
            formatted.append(f"[{i:02d}] {instance_id}")
            formatted.append(f"     Created: {created_at}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching service instances: {str(e)}"

# Environment and Resource Management
@mcp.tool()
async def render_list_env_groups() -> str:
    """
    🔧 List all environment groups in your Render account.

    Returns:
        List of environment groups that can be shared across services
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/env-groups"
        response = await run_curl(url)

        env_groups = response if isinstance(response, list) else []

        if not env_groups:
            return "🔧 No environment groups found in your account\n💡 Environment groups allow sharing env vars across multiple services"

        formatted = []
        formatted.append("🔧 Environment Groups")
        formatted.append("═" * 40)

        for i, group_data in enumerate(env_groups, 1):
            group = group_data.get('envGroup', {})
            name = group.get('name', 'Unknown')
            created_at = group.get('createdAt', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Created: {created_at}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching environment groups: {str(e)}"

@mcp.tool()
async def render_list_disks() -> str:
    """
    💾 List all persistent disks in your Render account.

    Returns:
        List of persistent disks for data storage
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/disks"
        response = await run_curl(url)

        disks = response if isinstance(response, list) else []

        if not disks:
            return "💾 No persistent disks found in your account\n💡 Persistent disks provide storage that survives service restarts"

        formatted = []
        formatted.append("💾 Persistent Disks")
        formatted.append("═" * 30)

        for i, disk_data in enumerate(disks, 1):
            disk = disk_data.get('disk', {})
            name = disk.get('name', 'Unknown')
            size = disk.get('sizeGB', 'Unknown')
            mount_path = disk.get('mountPath', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Size: {size}GB")
            formatted.append(f"     Mount: {mount_path}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching disks: {str(e)}"

@mcp.tool()
async def render_list_projects() -> str:
    """
    📁 List all projects in your Render account.

    Returns:
        List of projects for organizing services
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/projects"
        response = await run_curl(url)

        projects = response if isinstance(response, list) else []

        if not projects:
            return "📁 No projects found in your account"

        formatted = []
        formatted.append("📁 Projects")
        formatted.append("═" * 20)

        for i, project_data in enumerate(projects, 1):
            project = project_data.get('project', {})
            name = project.get('name', 'Unknown')
            created_at = project.get('createdAt', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Created: {created_at}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching projects: {str(e)}"

@mcp.tool()
async def render_get_user_info() -> str:
    """
    👤 Get current user account information.

    Returns:
        Your Render account details
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/users"
        response = await run_curl(url)

        if not response:
            return "❌ No user information found"

        email = response.get('email', 'Unknown')
        name = response.get('name', 'Unknown')

        formatted = []
        formatted.append("👤 User Account Information")
        formatted.append("═" * 35)
        formatted.append(f"📧 Email: {email}")
        formatted.append(f"👤 Name: {name}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching user info: {str(e)}"

@mcp.tool()
async def render_list_maintenance_windows() -> str:
    """
    🔧 List scheduled maintenance windows.

    Returns:
        Information about planned Render platform maintenance
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/maintenance"
        response = await run_curl(url)

        maintenance = response if isinstance(response, list) else []

        if not maintenance:
            return "🔧 No scheduled maintenance windows\n✅ All systems operational"

        formatted = []
        formatted.append("🔧 Scheduled Maintenance")
        formatted.append("═" * 30)

        for i, maint in enumerate(maintenance, 1):
            title = maint.get('title', 'Unknown')
            start_time = maint.get('startTime', 'Unknown')
            end_time = maint.get('endTime', 'Unknown')
            formatted.append(f"[{i:02d}] {title}")
            formatted.append(f"     Start: {start_time}")
            formatted.append(f"     End: {end_time}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching maintenance info: {str(e)}"

@mcp.tool()
async def render_delete_service(service_id: str) -> str:
    """
    🗑️ Delete a Render service permanently.

    CAUTION: This action is irreversible and will permanently delete the service.

    Args:
        service_id: Service ID to delete (required for safety)

    Returns:
        Deletion operation result
    """
    try:
        if not service_id:
            return "❌ Service ID is required for deletion (safety measure)"

        # First get service info to confirm what we're deleting
        service_url = f"{RENDER_BASE_URL}/v1/services/{service_id}"
        service_response = await run_curl(service_url)
        service_name = service_response.get('name', 'Unknown')
        service_type = service_response.get('type', 'Unknown')

        # Perform deletion
        delete_url = f"{RENDER_BASE_URL}/v1/services/{service_id}"
        response = await run_curl(delete_url, method="DELETE")

        return f"🗑️ Service '{service_name}' ({service_type}) has been permanently deleted\n⚠️ Service ID: {service_id}\n💡 This action cannot be undone"

    except Exception as e:
        if "404" in str(e):
            return f"❌ Service {service_id} not found - it may already be deleted"
        return f"❌ Error deleting service: {str(e)}"

@mcp.tool()
async def render_logs(
    service_id: Optional[str] = None,
    limit: int = 20,
    service_type: str = "web"
) -> str:
    """
    Get recent service runtime logs.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID for web, BACKGROUND_SERVICE_ID for background)
        limit: Number of recent log entries to show (max 100)
        service_type: Either 'web' or 'background' to choose which service

    Returns:
        Formatted service logs with timestamps and log levels
    """
    try:
        # Determine target service ID
        if service_id:
            target_service_id = service_id
        elif service_type == "background":
            target_service_id = BACKGROUND_SERVICE_ID
            if not target_service_id:
                return "❌ BACKGROUND_SERVICE_ID not configured in environment"
        else:
            target_service_id = SERVICE_ID

        limit = min(limit, 100)

        url = f"{RENDER_BASE_URL}/v1/logs?ownerId={OWNER_ID}&resource={target_service_id}&limit={limit}"
        response = await run_curl(url)

        logs = response.get('logs', [])
        if not logs:
            return f"No logs found for service {target_service_id}"

        # Format logs
        service_name = "Background Service" if service_type == 'background' else "Web Service"
        formatted = []
        formatted.append(f"📋 {service_name} Logs: {target_service_id}")
        formatted.append(f"📊 Showing {len(logs)} most recent entries")
        formatted.append("\n" + "="*80 + "\n")

        # Reverse to show oldest first (chronological order)
        for log in reversed(logs):
            timestamp = log.get('timestamp', '')
            message = log.get('message', '')
            level = 'info'

            # Extract level from labels
            for label in log.get('labels', []):
                if label.get('name') == 'level':
                    level = label.get('value', 'info')
                    break

            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp[:8] if timestamp else "??:??:??"

            # Level emoji
            level_emoji = {
                'info': '💬',
                'error': '❌',
                'warn': '⚠️',
                'warning': '⚠️',
                'debug': '🔍'
            }.get(level.lower(), '📝')

            formatted.append(f"{level_emoji} {time_str} | {message}")

        if response.get('hasMore'):
            formatted.append("\n📋 More logs available (use higher --limit to get more)")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching logs: {str(e)}"


@mcp.tool()
async def search_render_logs(
    search_term: str,
    service_id: Optional[str] = None,
    limit: int = 50,
    service_type: str = "web"
) -> str:
    """
    Search recent logs for specific text patterns.

    Args:
        search_term: Text to search for in log messages (case-insensitive)
        service_id: Render service ID (defaults to configured SERVICE_ID)
        limit: Number of recent log entries to search through (max 200)
        service_type: Either 'web' or 'background' to choose which service

    Returns:
        Filtered logs containing the search term
    """
    try:
        # Get logs using the existing tool
        all_logs = await render_logs(service_id=service_id, limit=limit, service_type=service_type)

        if all_logs.startswith("❌"):
            return all_logs

        # Filter logs containing search term
        lines = all_logs.split('\n')
        header_lines = lines[:3]  # Keep the header
        log_lines = lines[4:]     # Skip header and separator

        search_lower = search_term.lower()
        matching_lines = [line for line in log_lines if search_lower in line.lower()]

        if not matching_lines:
            return f"🔍 No logs found containing '{search_term}'"

        # Reconstruct with new header
        formatted = []
        formatted.extend(header_lines[:2])  # Service name and count lines
        formatted[1] = f"🔍 Found {len(matching_lines)} entries matching '{search_term}'"
        formatted.append(lines[2])  # Separator line
        formatted.extend(matching_lines)

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error searching logs: {str(e)}"


@mcp.tool()
async def render_recent_errors(
    service_id: Optional[str] = None,
    limit: int = 50,
    service_type: str = "web"
) -> str:
    """
    Get recent error and warning logs only.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        limit: Number of recent log entries to search through (max 200)
        service_type: Either 'web' or 'background' to choose which service

    Returns:
        Filtered logs showing only errors and warnings
    """
    try:
        # Get logs using the existing tool
        all_logs = await render_logs(service_id=service_id, limit=limit, service_type=service_type)

        if all_logs.startswith("❌"):
            return all_logs

        # Filter for error/warning lines
        lines = all_logs.split('\n')
        header_lines = lines[:3]  # Keep the header
        log_lines = lines[4:]     # Skip header and separator

        error_lines = [line for line in log_lines if line.startswith(('❌', '⚠️'))]

        if not error_lines:
            return f"✅ No recent errors or warnings found in last {limit} log entries"

        # Reconstruct with new header
        formatted = []
        formatted.extend(header_lines[:2])
        formatted[1] = f"⚠️ Found {len(error_lines)} errors/warnings in recent logs"
        formatted.append(lines[2])  # Separator line
        formatted.extend(error_lines)

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching error logs: {str(e)}"


@mcp.tool()
async def render_latest_deployment_logs(service_id: Optional[str] = None, lines: int = 30) -> str:
    """
    Get logs from the most recent deployment for debugging deployment issues.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        lines: Number of recent log lines to show from latest deployment

    Returns:
        Recent logs that may help debug deployment issues
    """
    try:
        target_service_id = service_id or SERVICE_ID

        # Get recent deployments to find the latest one
        deployments_result = await render_deployments(service_id=target_service_id, limit=1)

        if deployments_result.startswith("❌"):
            return deployments_result

        # Get recent logs (more than requested to account for non-deployment logs)
        logs_result = await render_logs(service_id=target_service_id, limit=lines * 2)

        if logs_result.startswith("❌"):
            return logs_result

        # Format for deployment context
        formatted = []
        formatted.append(f"🚀 Latest Deployment Logs: {target_service_id}")
        formatted.append(f"📊 Showing recent {lines} deployment-related entries")
        formatted.append("\n" + "="*80 + "\n")

        # Extract log lines and take the most recent ones
        lines_list = logs_result.split('\n')[4:]  # Skip header
        recent_lines = [line for line in lines_list if line.strip()][-lines:]

        formatted.extend(recent_lines)

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching deployment logs: {str(e)}"


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