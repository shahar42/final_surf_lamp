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
from deploy_tools import register_deployment_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("render-mcp")

# Initialize FastMCP server
mcp = FastMCP("render")

# Register deployment tools
register_deployment_tools(mcp)

# Configuration
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("SERVICE_ID", "srv-d2chm8mr433s73anlc0g")
OWNER_ID = os.getenv("OWNER_ID")
BACKGROUND_SERVICE_ID = os.getenv("BACKGROUND_SERVICE_ID")

if not RENDER_API_KEY:
    logger.error("ERROR: RENDER_API_KEY environment variable is required")
    sys.exit(1)
if not OWNER_ID:
    logger.error("ERROR: OWNER_ID environment variable is required for log access")
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

        # Debug: Add response structure info for troubleshooting
        if not isinstance(response, (list, dict)) or (isinstance(response, dict) and not response):
            return f"ERROR: Unexpected API response format for service {target_service_id}: {type(response)}"

        # Handle various API response formats
        if isinstance(response, list):
            deployments = response
        elif isinstance(response, dict):
            # Check for wrapped deployments
            deployments = response.get('deploys', response.get('data', []))
            # If still empty, check if each item has a 'deploy' wrapper
            if not deployments and response:
                deployments = [response]
        else:
            deployments = []

        if not deployments:
            return f"No deployments found for service {target_service_id}"

        # Format deployment history
        formatted = []
        formatted.append(f"Recent Deployments for Service: {target_service_id}")
        formatted.append(f"Showing {len(deployments)} most recent deployments")
        formatted.append("\n" + "="*80 + "\n")

        for i, deploy_item in enumerate(deployments, 1):
            # Handle deploy being wrapped in another structure
            if isinstance(deploy_item, dict) and 'deploy' in deploy_item:
                deploy = deploy_item['deploy']
            else:
                deploy = deploy_item

            # Safe extraction with type checking
            deploy_id = deploy.get('id', 'Unknown') if isinstance(deploy, dict) else 'Unknown'
            status = deploy.get('status', 'Unknown') if isinstance(deploy, dict) else 'Unknown'
            created_at = deploy.get('createdAt', 'Unknown') if isinstance(deploy, dict) else 'Unknown'
            finished_at = deploy.get('finishedAt', 'In Progress') if isinstance(deploy, dict) else 'In Progress'

            # Status mapping
            status_prefix = {
                'live': 'LIVE',
                'build_failed': 'FAILED',
                'build_in_progress': 'BUILDING',
                'canceled': 'CANCELED',
                'pre_deploy_failed': 'DEPLOY_FAILED',
                'created': 'CREATED',
                'build_successful': 'BUILD_OK',
                'deploy_started': 'DEPLOYING',
                'deploy_failed': 'DEPLOY_FAILED',
                'deploy_successful': 'DEPLOYED'
            }.get(status.lower() if status != 'Unknown' else 'unknown', 'UNKNOWN')

            formatted.append(f"[{i:02d}] {status_prefix} Deploy {deploy_id}")
            formatted.append(f"     Status: {status}")
            formatted.append(f"     Created: {created_at}")
            formatted.append(f"     Finished: {finished_at}")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        return f"Error fetching deployments: {str(e)}"

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
        formatted.append(f"INFO: Service Status: {target_service_id}")
        formatted.append(f"SUCCESS: {name}")
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
        return f"ERROR: Error fetching service status: {str(e)}"


@mcp.tool()
async def render_service_events(service_id: Optional[str] = None, limit: int = 20) -> str:
    """
    DEBUG: Intelligent service events analysis with actionable insights.

    ENHANCED FOR LLM USE: Provides structured, actionable insights instead of raw event data.
    Automatically categorizes issues, suggests solutions, and highlights what needs attention.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)
        limit: Number of recent events to analyze (max 50)

    Returns:
        Structured analysis with status summary, problems, and recommended actions
    """
    try:
        target_service_id = service_id or SERVICE_ID
        limit = min(limit, 50)

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/events?limit={limit}"
        response = await run_curl(url)

        events = response if isinstance(response, list) else response.get('events', [])

        if not events:
            return f"LIST: No events found for service {target_service_id}\nTIP: This could indicate a new service or connection issues"

        # Analyze events for patterns
        deployments = []
        health_issues = []
        recent_problems = []

        for event_data in events:
            event = event_data.get('event', {})
            event_type = event.get('type', 'Unknown')
            timestamp = event.get('timestamp', 'Unknown')
            details = event.get('details', {})

            if 'deploy' in event_type:
                status = details.get('deployStatus', 'unknown')
                deployments.append({'type': event_type, 'status': status, 'time': timestamp})

            if 'unhealthy' in event_type or 'failed' in event_type.lower():
                recent_problems.append({'type': event_type, 'time': timestamp, 'details': details})

            if 'server_' in event_type:
                health_issues.append({'type': event_type, 'time': timestamp})

        # Generate intelligent summary
        formatted = []
        formatted.append(f"INTELLIGENT SERVICE ANALYSIS: {target_service_id}")
        formatted.append("=" * 60)

        # Overall Status Assessment
        recent_failures = len([p for p in recent_problems if any(keyword in p['type'].lower() for keyword in ['fail', 'error', 'unhealthy'])])
        if recent_failures == 0:
            formatted.append("STATUS: HEALTHY - No recent issues detected")
        elif recent_failures <= 2:
            formatted.append("STATUS: MINOR ISSUES - Some problems but service recovering")
        else:
            formatted.append("STATUS: NEEDS ATTENTION - Multiple recent failures")

        # Deployment Analysis
        if deployments:
            latest_deploy = deployments[0]
            deploy_status = latest_deploy.get('status', 'unknown')

            formatted.append(f"\nDEPLOYMENT STATUS:")
            if deploy_status == 'live':
                formatted.append("   Latest deployment: SUCCESSFUL")
            elif 'fail' in deploy_status:
                formatted.append("   Latest deployment: FAILED")
                formatted.append("   Action: Check build logs and fix deployment issues")
            else:
                formatted.append(f"   Latest deployment: {deploy_status.upper()}")

            total_deployments = len(deployments)
            failed_deployments = len([d for d in deployments if 'fail' in d.get('status', '')])
            if failed_deployments > 0:
                formatted.append(f"   Recent activity: {failed_deployments}/{total_deployments} deployments failed")

        # Health Analysis
        if health_issues:
            unhealthy_events = len([h for h in health_issues if 'unhealthy' in h['type']])
            healthy_events = len([h for h in health_issues if 'healthy' in h['type']])

            formatted.append(f"\nHEALTH MONITORING:")
            if unhealthy_events > healthy_events:
                formatted.append("   Stability concern: More unhealthy than healthy events")
                formatted.append("   Action: Monitor resource usage, consider scaling up")
            elif healthy_events > 0:
                formatted.append("   Recovery detected: Service self-healing properly")
            else:
                formatted.append("   Health status: No significant health events")

        # Problem Summary & Actions
        if recent_problems:
            formatted.append(f"\nRECENT PROBLEMS ({len(recent_problems)} found):")
            problem_types = {}
            for problem in recent_problems:
                ptype = problem['type']
                problem_types[ptype] = problem_types.get(ptype, 0) + 1

            for ptype, count in problem_types.items():
                formatted.append(f"   - {ptype}: {count} occurrences")

            formatted.append(f"\nRECOMMENDED ACTIONS:")
            if any('deploy' in p['type'] for p in recent_problems):
                formatted.append("   - Check deployment configuration and build process")
            if any('server' in p['type'] for p in recent_problems):
                formatted.append("   - Monitor server resources (CPU, memory, disk)")
                formatted.append("   - Consider upgrading service plan if resource-related")
            formatted.append("   - Review recent commits for potential code issues")

        else:
            formatted.append(f"\nNO PROBLEMS DETECTED")
            formatted.append("   Service appears to be running smoothly")

        # Quick Action Summary
        formatted.append(f"\nQUICK STATUS:")
        action_needed = recent_failures > 0 or len([d for d in deployments if 'fail' in d.get('status', '')]) > 0
        if action_needed:
            formatted.append("   ACTION REQUIRED: Issues need investigation")
        else:
            formatted.append("   NO ACTION NEEDED: Service operating normally")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error analyzing service events: {str(e)}"

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
        formatted.append(f"CONFIG: Environment Variables: {target_service_id}")
        formatted.append(f"INFO: Found {len(env_vars)} environment variables")
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
        return f"ERROR: Error fetching environment variables: {str(e)}"

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
        formatted.append(f"SERVICES: All Render Services")
        formatted.append(f"INFO: Found {len(services)} services")
        formatted.append("\n" + "="*80 + "\n")

        for i, service_data in enumerate(services, 1):
            service = service_data.get('service', {})
            service_id = service.get('id', 'Unknown')
            name = service.get('name', 'Unknown')
            service_type = service.get('type', 'Unknown')
            created_at = service.get('createdAt', 'Unknown')

            # Service type emoji
            type_emoji = {
                'web_service': 'WEB:',
                'background_worker': 'WORKER:',
                'private_service': '🔒',
                'static_site': 'FILE:'
            }.get(service_type, 'LIST:')

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
        return f"ERROR: Error listing services: {str(e)}"

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
        formatted.append(f"DEPLOY: Deployment Details: {deploy_id}")
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
            formatted.append("\nNOTE: Commit Information:")
            formatted.append(f"Hash: {commit.get('id', 'Unknown')}")
            formatted.append(f"Message: {commit.get('message', 'No message')}")
            formatted.append(f"Created: {commit.get('createdAt', 'Unknown')}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching deployment details: {str(e)}"

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
        status_emoji = "SUCCESS:" if service['suspended'] == 'not_suspended' else "SUSPENDED:"
        type_emoji = {
            'web_service': 'WEB:',
            'background_worker': 'WORKER:',
            'private_service': '🔒',
            'static_site': 'FILE:'
        }.get(service['type'], 'LIST:')

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
async def render_services_status(analysis_level: str = "summary") -> str:
    """
    SERVICES: Smart service status tool that adapts output based on your needs.

    USAGE GUIDANCE:
    - Use "summary" for quick health checks and cost overview
    - Use "detailed" for deep investigation and troubleshooting
    - Use "problems" to focus only on services needing attention

    Args:
        analysis_level: "summary" (default), "detailed", or "problems"

    Returns:
        Intelligent service analysis tailored to your investigation needs
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
        problem_services = [s for s in services if s['suspended'] != 'not_suspended' and s['cost'] > 0]

        if analysis_level == "problems":
            if not problem_services:
                return "ALL SERVICES HEALTHY\nNo issues detected - all services running normally"

            formatted = []
            formatted.append("SERVICES NEEDING ATTENTION")
            formatted.append("=" * 40)
            formatted.append(f"Problems Found: {len(problem_services)}")
            wasted_cost = sum(s['cost'] for s in problem_services)
            formatted.append(f"Money Being Wasted: ${wasted_cost:.2f}/month")
            formatted.append("\nACTION REQUIRED:")

            for service in problem_services:
                formatted.append(f"   {service['name']}: SUSPENDED but still billing ${service['cost']}/mo")
                formatted.append(f"      Recommended: Delete or resume this service")

            return "\n".join(formatted)

        elif analysis_level == "detailed":
            formatted = []
            formatted.append("DEBUG: DETAILED SERVICE ANALYSIS")
            formatted.append("═" * 60)
            formatted.append(f"INFO: Total: {total_services} | SUCCESS: Active: {active_services} | COST: Cost: ${total_cost:.2f}/mo")
            formatted.append("\n" + "─" * 60 + "\n")
            formatted.append(_format_service_list(services, detailed=True))

            if problem_services:
                formatted.append(f"\nWARNING: ATTENTION NEEDED: {len(problem_services)} services have issues")

            return "\n".join(formatted)

        else:  # summary (default)
            web_services = len([s for s in services if s['type'] == 'web_service'])
            workers = len([s for s in services if s['type'] == 'background_worker'])

            formatted = []
            formatted.append("SERVICES: SERVICES SUMMARY")
            formatted.append("═" * 30)
            formatted.append(f"INFO: Total: {total_services} | SUCCESS: Active: {active_services}")
            if suspended_services > 0:
                formatted.append(f"SUSPENDED: Suspended: {suspended_services}")
            formatted.append(f"COST: Monthly Cost: ${total_cost:.2f}")
            formatted.append(f"WEB: Web: {web_services} | WORKER: Workers: {workers}")

            if problem_services:
                formatted.append(f"ALERT: Issues: {len(problem_services)} services need attention")
                formatted.append("TIP: Use analysis_level='problems' for details")
            else:
                formatted.append("SUCCESS: All services healthy")

            formatted.append("\n" + "─" * 30)
            formatted.append(_format_service_list(services))

            return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching services status: {str(e)}"


@mcp.tool()
async def render_services_cost_analysis() -> str:
    """
    COST: Analyze costs across all services with optimization suggestions.

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
        formatted.append("COST: Cost Analysis Report")
        formatted.append("═" * 40)
        formatted.append(f"💸 Total Monthly Cost: ${total_cost:.2f}")
        formatted.append(f"💳 Paid Services: {len(paid_services)}")
        formatted.append(f"🆓 Free Services: {len(free_services)}")

        if suspended_paid:
            wasted_cost = sum(s['cost'] for s in suspended_paid)
            formatted.append(f"WARNING: Suspended Paid Services: ${wasted_cost:.2f}/mo wasted")

        formatted.append("\nINFO: Cost Breakdown:")
        for service in paid_services:
            status = "SUSPENDED: SUSPENDED" if service['suspended'] != 'not_suspended' else "SUCCESS: Active"
            formatted.append(f"   ${service['cost']:.0f}/mo - {service['name']} ({status})")

        # Optimization suggestions
        if suspended_paid:
            formatted.append("\nTIP: Optimization Suggestions:")
            formatted.append("   • Consider deleting suspended paid services")
            for service in suspended_paid:
                formatted.append(f"     - {service['name']}: ${service['cost']:.0f}/mo savings")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error analyzing costs: {str(e)}"

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
            status = "SUCCESS:" if service['suspended'] == 'not_suspended' else "SUSPENDED:"
            formatted.append(f"{status} {service['name']} ({service['type']})")
            formatted.append(f"   ssh {service['ssh_address']}")
            formatted.append(f"   Region: {service['region']}")
            formatted.append("")

        formatted.append("TIP: Usage: Copy the SSH command to connect directly to your service")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching SSH info: {str(e)}"

# Service Management Tools
@mcp.tool()
async def render_restart_service(service_id: Optional[str] = None) -> str:
    """
    RESTART: Restart a Render service.

    Args:
        service_id: Service ID to restart (defaults to configured SERVICE_ID)

    Returns:
        Restart operation result
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/restart"
        response = await run_curl(url, method="POST")

        return f"SUCCESS: Service restart initiated for {target_service_id}\nRESTART: Service will restart momentarily"

    except Exception as e:
        return f"ERROR: Error restarting service: {str(e)}"

@mcp.tool()
async def render_suspend_service(service_id: Optional[str] = None) -> str:
    """
    SUSPENDED: Suspend a Render service (stops it from running).

    Args:
        service_id: Service ID to suspend (defaults to configured SERVICE_ID)

    Returns:
        Suspend operation result
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/suspend"
        response = await run_curl(url, method="POST")

        return f"SUSPENDED: Service suspension initiated for {target_service_id}\nCOST: Service will stop running and billing will pause"

    except Exception as e:
        return f"ERROR: Error suspending service: {str(e)}"

@mcp.tool()
async def render_resume_service(service_id: Optional[str] = None) -> str:
    """
    RESUME: Resume a suspended Render service.

    Args:
        service_id: Service ID to resume (defaults to configured SERVICE_ID)

    Returns:
        Resume operation result
    """
    try:
        target_service_id = service_id or SERVICE_ID

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/resume"
        response = await run_curl(url, method="POST")

        return f"RESUME: Service resume initiated for {target_service_id}\nDEPLOY: Service will start up shortly (30-60 seconds)"

    except Exception as e:
        return f"ERROR: Error resuming service: {str(e)}"

@mcp.tool()
async def render_scale_service(num_instances: int, service_id: Optional[str] = None) -> str:
    """
    INFO: Scale a Render service to specified number of instances.

    Args:
        num_instances: Number of instances (0 to stop, 1+ to scale up)
        service_id: Service ID to scale (defaults to configured SERVICE_ID)

    Returns:
        Scaling operation result with cost implications
    """
    try:
        target_service_id = service_id or SERVICE_ID

        if num_instances < 0:
            return "ERROR: Number of instances must be 0 or greater"

        url = f"{RENDER_BASE_URL}/v1/services/{target_service_id}/scale"
        data = {"numInstances": num_instances}
        response = await run_curl(url, method="POST", data=data)

        if num_instances == 0:
            message = f"🛑 Service {target_service_id} scaled to 0 instances\nCOST: Service stopped - no charges while scaled to 0"
        elif num_instances == 1:
            message = f"INFO: Service {target_service_id} scaled to 1 instance\nCOST: Normal billing applies"
        else:
            message = f"📈 Service {target_service_id} scaled to {num_instances} instances\nCOST: Higher billing - {num_instances}x instance cost"

        return message

    except Exception as e:
        return f"ERROR: Error scaling service: {str(e)}"

@mcp.tool()
async def render_get_custom_domains(service_id: Optional[str] = None) -> str:
    """
    WEB: List custom domains configured for a service.

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
            return f"WEB: No custom domains configured for service {target_service_id}\nTIP: Using default .onrender.com domain"

        formatted = []
        formatted.append(f"WEB: Custom Domains for {target_service_id}")
        formatted.append("═" * 50)

        for i, domain in enumerate(domains, 1):
            domain_name = domain.get('name', 'Unknown')
            status = domain.get('verificationStatus', 'Unknown')
            formatted.append(f"[{i:02d}] {domain_name} - {status}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching custom domains: {str(e)}"

@mcp.tool()
async def render_get_secret_files(service_id: Optional[str] = None) -> str:
    """
    FILE: List secret files configured for a service.

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
            return f"FILE: No secret files configured for service {target_service_id}"

        formatted = []
        formatted.append(f"FILE: Secret Files for {target_service_id}")
        formatted.append("═" * 50)

        for i, file_data in enumerate(files, 1):
            file_info = file_data.get('secretFile', {})
            name = file_info.get('name', 'Unknown')
            path = file_info.get('path', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Path: {path}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching secret files: {str(e)}"

@mcp.tool()
async def render_get_service_instances(service_id: Optional[str] = None) -> str:
    """
    INSTANCE: List running instances for a service.

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
            return f"INSTANCE: No running instances found for service {target_service_id}"

        formatted = []
        formatted.append(f"INSTANCE: Service Instances for {target_service_id}")
        formatted.append("═" * 50)

        for i, instance in enumerate(instances, 1):
            instance_id = instance.get('id', 'Unknown')
            created_at = instance.get('createdAt', 'Unknown')
            formatted.append(f"[{i:02d}] {instance_id}")
            formatted.append(f"     Created: {created_at}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching service instances: {str(e)}"

# Environment and Resource Management
@mcp.tool()
async def render_list_env_groups() -> str:
    """
    CONFIG: List all environment groups in your Render account.

    Returns:
        List of environment groups that can be shared across services
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/env-groups"
        response = await run_curl(url)

        env_groups = response if isinstance(response, list) else []

        if not env_groups:
            return "CONFIG: No environment groups found in your account\nTIP: Environment groups allow sharing env vars across multiple services"

        formatted = []
        formatted.append("CONFIG: Environment Groups")
        formatted.append("═" * 40)

        for i, group_data in enumerate(env_groups, 1):
            group = group_data.get('envGroup', {})
            name = group.get('name', 'Unknown')
            created_at = group.get('createdAt', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Created: {created_at}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching environment groups: {str(e)}"

@mcp.tool()
async def render_list_disks() -> str:
    """
    DISK: List all persistent disks in your Render account.

    Returns:
        List of persistent disks for data storage
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/disks"
        response = await run_curl(url)

        disks = response if isinstance(response, list) else []

        if not disks:
            return "DISK: No persistent disks found in your account\nTIP: Persistent disks provide storage that survives service restarts"

        formatted = []
        formatted.append("DISK: Persistent Disks")
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
        return f"ERROR: Error fetching disks: {str(e)}"

@mcp.tool()
async def render_list_projects() -> str:
    """
    PROJECT: List all projects in your Render account.

    Returns:
        List of projects for organizing services
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/projects"
        response = await run_curl(url)

        projects = response if isinstance(response, list) else []

        if not projects:
            return "PROJECT: No projects found in your account"

        formatted = []
        formatted.append("PROJECT: Projects")
        formatted.append("═" * 20)

        for i, project_data in enumerate(projects, 1):
            project = project_data.get('project', {})
            name = project.get('name', 'Unknown')
            created_at = project.get('createdAt', 'Unknown')
            formatted.append(f"[{i:02d}] {name}")
            formatted.append(f"     Created: {created_at}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching projects: {str(e)}"

@mcp.tool()
async def render_get_user_info() -> str:
    """
    USER: Get current user account information.

    Returns:
        Your Render account details
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/users"
        response = await run_curl(url)

        if not response:
            return "ERROR: No user information found"

        email = response.get('email', 'Unknown')
        name = response.get('name', 'Unknown')

        formatted = []
        formatted.append("USER: User Account Information")
        formatted.append("═" * 35)
        formatted.append(f"📧 Email: {email}")
        formatted.append(f"USER: Name: {name}")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching user info: {str(e)}"

@mcp.tool()
async def render_list_maintenance_windows() -> str:
    """
    CONFIG: List scheduled maintenance windows.

    Returns:
        Information about planned Render platform maintenance
    """
    try:
        url = f"{RENDER_BASE_URL}/v1/maintenance"
        response = await run_curl(url)

        maintenance = response if isinstance(response, list) else []

        if not maintenance:
            return "CONFIG: No scheduled maintenance windows\nSUCCESS: All systems operational"

        formatted = []
        formatted.append("CONFIG: Scheduled Maintenance")
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
        return f"ERROR: Error fetching maintenance info: {str(e)}"

@mcp.tool()
async def render_delete_service(service_id: str) -> str:
    """
    DELETE: Delete a Render service permanently.

    CAUTION: This action is irreversible and will permanently delete the service.

    Args:
        service_id: Service ID to delete (required for safety)

    Returns:
        Deletion operation result
    """
    try:
        if not service_id:
            return "ERROR: Service ID is required for deletion (safety measure)"

        # First get service info to confirm what we're deleting
        service_url = f"{RENDER_BASE_URL}/v1/services/{service_id}"
        service_response = await run_curl(service_url)
        service_name = service_response.get('name', 'Unknown')
        service_type = service_response.get('type', 'Unknown')

        # Perform deletion
        delete_url = f"{RENDER_BASE_URL}/v1/services/{service_id}"
        response = await run_curl(delete_url, method="DELETE")

        return f"DELETE: Service '{service_name}' ({service_type}) has been permanently deleted\nWARNING: Service ID: {service_id}\nTIP: This action cannot be undone"

    except Exception as e:
        if "404" in str(e):
            return f"ERROR: Service {service_id} not found - it may already be deleted"
        return f"ERROR: Error deleting service: {str(e)}"

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
                return "ERROR: BACKGROUND_SERVICE_ID not configured in environment"
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
        formatted.append(f"LIST: {service_name} Logs: {target_service_id}")
        formatted.append(f"INFO: Showing {len(logs)} most recent entries")
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
                'info': 'LOG:',
                'error': 'ERROR:',
                'warn': 'WARNING:',
                'warning': 'WARNING:',
                'debug': 'DEBUG:'
            }.get(level.lower(), 'NOTE:')

            formatted.append(f"{level_emoji} {time_str} | {message}")

        if response.get('hasMore'):
            formatted.append("\nLIST: More logs available (use higher --limit to get more)")

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching logs: {str(e)}"


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

        if all_logs.startswith("ERROR:"):
            return all_logs

        # Filter logs containing search term
        lines = all_logs.split('\n')
        header_lines = lines[:3]  # Keep the header
        log_lines = lines[4:]     # Skip header and separator

        search_lower = search_term.lower()
        matching_lines = [line for line in log_lines if search_lower in line.lower()]

        if not matching_lines:
            return f"DEBUG: No logs found containing '{search_term}'"

        # Reconstruct with new header
        formatted = []
        formatted.extend(header_lines[:2])  # Service name and count lines
        formatted[1] = f"DEBUG: Found {len(matching_lines)} entries matching '{search_term}'"
        formatted.append(lines[2])  # Separator line
        formatted.extend(matching_lines)

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error searching logs: {str(e)}"


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

        if all_logs.startswith("ERROR:"):
            return all_logs

        # Filter for error/warning lines
        lines = all_logs.split('\n')
        header_lines = lines[:3]  # Keep the header
        log_lines = lines[4:]     # Skip header and separator

        error_lines = [line for line in log_lines if line.startswith(('ERROR:', 'WARNING:'))]

        if not error_lines:
            return f"SUCCESS: No recent errors or warnings found in last {limit} log entries"

        # Reconstruct with new header
        formatted = []
        formatted.extend(header_lines[:2])
        formatted[1] = f"WARNING: Found {len(error_lines)} errors/warnings in recent logs"
        formatted.append(lines[2])  # Separator line
        formatted.extend(error_lines)

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching error logs: {str(e)}"


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

        if deployments_result.startswith("ERROR:"):
            return deployments_result

        # Get recent logs (more than requested to account for non-deployment logs)
        logs_result = await render_logs(service_id=target_service_id, limit=lines * 2)

        if logs_result.startswith("ERROR:"):
            return logs_result

        # Format for deployment context
        formatted = []
        formatted.append(f"DEPLOY: Latest Deployment Logs: {target_service_id}")
        formatted.append(f"INFO: Showing recent {lines} deployment-related entries")
        formatted.append("\n" + "="*80 + "\n")

        # Extract log lines and take the most recent ones
        lines_list = logs_result.split('\n')[4:]  # Skip header
        recent_lines = [line for line in lines_list if line.strip()][-lines:]

        formatted.extend(recent_lines)

        return "\n".join(formatted)

    except Exception as e:
        return f"ERROR: Error fetching deployment logs: {str(e)}"


# Test API connection on startup
async def test_connection():
    """Test Render API connection on startup"""
    try:
        await render_service_status()
        logger.info("SUCCESS: Render API connection successful")
        return True
    except Exception as e:
        logger.error(f"ERROR: Render API connection failed: {e}")
        return False

logger.info("Render MCP Server initialized with FastMCP")

if __name__ == "__main__":
    # Test API connection
    asyncio.run(test_connection())

    # Run the FastMCP server
    logger.info("Starting Render MCP Server for Claude Code...")
    logger.info("MCP Server ready for Claude Code with FastMCP integration")
    mcp.run(transport='stdio')