#!/usr/bin/env python3
"""Debug script to test Render API session handling"""

import asyncio
import aiohttp
from config import settings

async def test_direct_api_call():
    """Test direct API call without MCP framework"""
    print(f"Testing API call to service: {settings.SERVICE_ID}")
    print(f"Base URL: {settings.RENDER_BASE_URL}")

    timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
    headers = {
        "Authorization": f"Bearer {settings.RENDER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession(
            base_url=settings.RENDER_BASE_URL,
            headers=headers,
            timeout=timeout
        ) as session:
            endpoint = f"services/{settings.SERVICE_ID}"
            print(f"Making request to: {endpoint}")

            async with session.get(endpoint) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")

                if response.status == 200:
                    data = await response.json()
                    print(f"Success! Service name: {data.get('name', 'Unknown')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"Error: {error_text}")
                    return False

    except Exception as e:
        print(f"Exception during API call: {e}")
        return False

async def test_render_client():
    """Test the render_client module"""
    print("\nTesting render_client module...")

    try:
        import render_client
        result = await render_client.get_service_status(settings.SERVICE_ID)
        print(f"render_client success: {result.get('name', 'Unknown')}")
        return True
    except Exception as e:
        print(f"render_client error: {e}")
        return False

if __name__ == "__main__":
    print("=== Render API Debug Test ===")

    # Test 1: Direct API call
    success1 = asyncio.run(test_direct_api_call())

    # Test 2: render_client module
    success2 = asyncio.run(test_render_client())

    print(f"\nResults:")
    print(f"Direct API call: {'✅' if success1 else '❌'}")
    print(f"render_client: {'✅' if success2 else '❌'}")