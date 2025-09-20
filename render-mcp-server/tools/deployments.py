"""MCP tools for Render deployments and service status"""

import json
from typing import Optional
from config import settings
import render_client


async def get_deployments(
    service_id: Optional[str] = None,
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
    try:
        target_service_id = service_id or settings.SERVICE_ID
        limit = min(limit, 50)

        response = await render_client.get_deployments(target_service_id, limit)
        deployments = response.get('deploys', [])

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
            commit = deploy.get('commit', {})
            commit_message = commit.get('message', 'No commit message')[:100]
            commit_id = commit.get('id', 'Unknown')[:8]

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
            formatted.append(f"     Commit: {commit_id} - {commit_message}")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching deployments: {str(e)}"


async def get_service_status(
    service_id: Optional[str] = None
) -> str:
    """
    Get current service status and health information.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Current service status and details
    """
    try:
        target_service_id = service_id or settings.SERVICE_ID

        response = await render_client.get_service_status(target_service_id)

        # Extract key information
        name = response.get('name', 'Unknown')
        status = response.get('status', 'Unknown')
        env = response.get('env', 'Unknown')
        region = response.get('region', 'Unknown')
        created_at = response.get('createdAt', 'Unknown')
        updated_at = response.get('updatedAt', 'Unknown')

        # Service type specific info
        service_type = response.get('type', 'Unknown')
        if service_type == 'web_service':
            url = response.get('serviceDetails', {}).get('url', 'No URL')
        else:
            url = 'N/A (Background Service)'

        # Build status summary
        status_emoji = {
            'active': '✅',
            'suspended': '⏸️',
            'failed': '❌',
            'building': '🔄'
        }.get(status, '❓')

        formatted = []
        formatted.append(f"📊 Service Status: {target_service_id}")
        formatted.append(f"{status_emoji} {name}")
        formatted.append("\n" + "="*50)
        formatted.append(f"Status: {status}")
        formatted.append(f"Type: {service_type}")
        formatted.append(f"Environment: {env}")
        formatted.append(f"Region: {region}")
        formatted.append(f"URL: {url}")
        formatted.append(f"Created: {created_at}")
        formatted.append(f"Last Updated: {updated_at}")

        # Add runtime info if available
        runtime = response.get('serviceDetails', {})
        if runtime:
            if 'numInstances' in runtime:
                formatted.append(f"Instances: {runtime['numInstances']}")
            if 'plan' in runtime:
                formatted.append(f"Plan: {runtime['plan']}")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching service status: {str(e)}"


async def get_latest_deployment_logs(
    service_id: Optional[str] = None
) -> str:
    """
    Get logs from the most recent deployment.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Logs from the latest deployment
    """
    try:
        target_service_id = service_id or settings.SERVICE_ID

        # Get the latest deployment
        deployments_response = await render_client.get_deployments(target_service_id, 1)
        deployments = deployments_response.get('deploys', [])

        if not deployments:
            return f"No deployments found for service {target_service_id}"

        latest_deploy = deployments[0]
        deploy_id = latest_deploy.get('id')
        status = latest_deploy.get('status')
        created_at = latest_deploy.get('createdAt')

        # Import logs tool to get logs from deployment time
        from .logs import get_render_logs
        from datetime import datetime, timedelta

        # Get logs from around deployment time (30 minutes window)
        deploy_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        start_time = (deploy_time - timedelta(minutes=5)).isoformat() + 'Z'
        end_time = (deploy_time + timedelta(minutes=25)).isoformat() + 'Z'

        logs = await get_render_logs(
            service_id=target_service_id,
            start_time=start_time,
            end_time=end_time,
            limit=100
        )

        result = []
        result.append(f"🚀 Latest Deployment Logs: {deploy_id}")
        result.append(f"Status: {status}")
        result.append(f"Deployed at: {created_at}")
        result.append("\n" + "="*60 + "\n")
        result.append(logs)

        return "\n".join(result)

    except Exception as e:
        return f"❌ Error fetching deployment logs: {str(e)}"