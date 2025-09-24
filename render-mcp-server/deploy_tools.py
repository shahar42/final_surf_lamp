"""
Render Service Deployment Tools
Full lifecycle management: create, configure, deploy services via API
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP

# Render API configuration
RENDER_BASE_URL = "https://api.render.com/v1"

async def make_render_request(
    method: str,
    endpoint: str,
    api_key: str,
    data: Optional[Dict] = None
) -> Dict:
    """Make authenticated request to Render API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    if data:
        headers["Content-Type"] = "application/json"

    url = f"{RENDER_BASE_URL}{endpoint}"

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            data=json.dumps(data) if data else None
        ) as response:
            response_text = await response.text()

            if not response.ok:
                raise Exception(f"Render API error {response.status}: {response_text}")

            try:
                return json.loads(response_text) if response_text else {}
            except json.JSONDecodeError:
                return {"message": response_text}

def register_deployment_tools(mcp: FastMCP):
    """Register deployment tools with FastMCP server"""

    @mcp.tool()
    async def create_background_worker(
        name: str,
        repo_url: str,
        build_command: str,
        start_command: str,
        env_vars: List[Dict[str, str]],
        branch: str = "master",
        runtime: str = "python",
        owner_id: str = "tea-ctl9m2rv2p9s738eghng",
        api_key: str = "rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s"
    ) -> str:
        """
        Create a new background worker service on Render.

        Args:
            name: Service name (e.g., 'surf-lamp-monitoring')
            repo_url: GitHub repository URL
            build_command: Command to build the service
            start_command: Command to start the service
            env_vars: List of environment variables [{"key": "NAME", "value": "VALUE"}]
            branch: Git branch to deploy from
            runtime: Service runtime (python, node, etc.)
            owner_id: Render owner/team ID
            api_key: Render API key
        """

        payload = {
            "type": "background_worker",
            "name": name,
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch,
            "runtime": runtime,
            "buildCommand": build_command,
            "startCommand": start_command,
            "autoDeploy": True,
            "envVars": env_vars
        }

        try:
            result = await make_render_request("POST", "/services", api_key, payload)
            service_id = result.get("service", {}).get("id", "unknown")
            service_name = result.get("service", {}).get("name", name)

            return f"""✅ Background Worker Created Successfully!

🆔 Service ID: {service_id}
📛 Service Name: {service_name}
🔗 Repository: {repo_url}
🌿 Branch: {branch}
🏗️ Build: {build_command}
▶️ Start: {start_command}
📦 Runtime: {runtime}
🔧 Environment Variables: {len(env_vars)} configured

The service is now building and will be available shortly.
Check the Render dashboard for build logs and deployment status.
"""
        except Exception as e:
            return f"❌ Failed to create background worker: {str(e)}"

    @mcp.tool()
    async def create_web_service(
        name: str,
        repo_url: str,
        build_command: str,
        start_command: str,
        env_vars: List[Dict[str, str]],
        branch: str = "master",
        runtime: str = "python",
        owner_id: str = "tea-ctl9m2rv2p9s738eghng",
        api_key: str = "rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s"
    ) -> str:
        """
        Create a new web service on Render.

        Args:
            name: Service name
            repo_url: GitHub repository URL
            build_command: Command to build the service
            start_command: Command to start the service
            env_vars: List of environment variables
            branch: Git branch to deploy from
            runtime: Service runtime
            owner_id: Render owner/team ID
            api_key: Render API key
        """

        payload = {
            "type": "web_service",
            "name": name,
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch,
            "runtime": runtime,
            "buildCommand": build_command,
            "startCommand": start_command,
            "autoDeploy": True,
            "envVars": env_vars
        }

        try:
            result = await make_render_request("POST", "/services", api_key, payload)
            service_id = result.get("service", {}).get("id", "unknown")
            service_name = result.get("service", {}).get("name", name)
            service_url = result.get("service", {}).get("serviceDetails", {}).get("url", "")

            return f"""✅ Web Service Created Successfully!

🆔 Service ID: {service_id}
📛 Service Name: {service_name}
🌐 Service URL: {service_url}
🔗 Repository: {repo_url}
🌿 Branch: {branch}
🏗️ Build: {build_command}
▶️ Start: {start_command}
📦 Runtime: {runtime}
🔧 Environment Variables: {len(env_vars)} configured

The service is now building and will be available at the URL above once deployed.
"""
        except Exception as e:
            return f"❌ Failed to create web service: {str(e)}"

    @mcp.tool()
    async def update_service_env_vars(
        service_id: str,
        env_vars: List[Dict[str, str]],
        api_key: str = "rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s"
    ) -> str:
        """
        Update environment variables for an existing service.

        Args:
            service_id: Render service ID
            env_vars: List of environment variables [{"key": "NAME", "value": "VALUE"}]
            api_key: Render API key
        """

        payload = {"envVars": env_vars}

        try:
            await make_render_request("PUT", f"/services/{service_id}/env-vars", api_key, payload)
            return f"""✅ Environment Variables Updated!

🆔 Service ID: {service_id}
🔧 Updated Variables: {len(env_vars)}

Variables:
{chr(10).join([f'  • {var["key"]}: {"***" if "password" in var["key"].lower() or "key" in var["key"].lower() else var["value"]}' for var in env_vars])}

The service will automatically redeploy with the new configuration.
"""
        except Exception as e:
            return f"❌ Failed to update environment variables: {str(e)}"

    @mcp.tool()
    async def trigger_deploy(
        service_id: str,
        clear_cache: bool = False,
        api_key: str = "rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s"
    ) -> str:
        """
        Trigger a manual deployment for a service.

        Args:
            service_id: Render service ID
            clear_cache: Whether to clear build cache
            api_key: Render API key
        """

        payload = {"clearCache": clear_cache}

        try:
            result = await make_render_request("POST", f"/services/{service_id}/deploys", api_key, payload)
            deploy_id = result.get("id", "unknown")

            return f"""✅ Deployment Triggered!

🆔 Service ID: {service_id}
🚀 Deploy ID: {deploy_id}
🧹 Cache Cleared: {'Yes' if clear_cache else 'No'}

The deployment is now in progress.
Check the Render dashboard for build logs and status updates.
"""
        except Exception as e:
            return f"❌ Failed to trigger deployment: {str(e)}"

    @mcp.tool()
    async def get_deploy_status(
        service_id: str,
        api_key: str = "rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s"
    ) -> str:
        """
        Get the status of recent deployments for a service.

        Args:
            service_id: Render service ID
            api_key: Render API key
        """

        try:
            result = await make_render_request("GET", f"/services/{service_id}/deploys", api_key)
            deploys = result.get("deploys", [])

            if not deploys:
                return f"📭 No deployments found for service {service_id}"

            output = [f"📊 Recent Deployments for {service_id}:\n"]

            for i, deploy in enumerate(deploys[:5]):  # Show last 5 deploys
                status = deploy.get("status", "unknown")
                created_at = deploy.get("createdAt", "")[:19].replace("T", " ")
                deploy_id = deploy.get("id", "")[:8]

                status_emoji = {
                    "created": "🔄",
                    "build_in_progress": "🏗️",
                    "build_successful": "✅",
                    "live": "🟢",
                    "build_failed": "❌",
                    "canceled": "⏹️"
                }.get(status, "❓")

                output.append(f"[{i+1}] {status_emoji} {deploy_id} - {status} - {created_at}")

            return "\n".join(output)

        except Exception as e:
            return f"❌ Failed to get deployment status: {str(e)}"