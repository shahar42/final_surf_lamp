#!/usr/bin/env python3
"""Test script for the new Render MCP server"""

import asyncio
import sys
import os

# Add current directory to path to import our server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render_mcp_server import (
    render_service_status, render_logs, render_deployments,
    render_service_events, render_environment_vars, render_list_all_services,
    render_deploy_details
)

async def main():
    print("Testing Render MCP Server...")
    print("=" * 50)

    # Test service status
    print("\n1. Testing service status:")
    try:
        status = await render_service_status()
        print(status)
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test recent logs
    print("\n2. Testing recent logs:")
    try:
        logs = await render_logs(limit=3)
        print(logs)
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test deployments
    print("\n3. Testing deployments:")
    try:
        deployments = await render_deployments(limit=2)
        print(deployments)
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test NEW TOOLS
    print("\n4. Testing service events:")
    try:
        events = await render_service_events(limit=5)
        print(events)
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n5. Testing environment variables:")
    try:
        env_vars = await render_environment_vars()
        print(env_vars)
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n6. Testing list all services:")
    try:
        all_services = await render_list_all_services()
        print(all_services)
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n7. Testing deploy details:")
    try:
        deploy_details = await render_deploy_details("dep-d37h8iemcj7s738sdrdg")
        print(deploy_details)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())