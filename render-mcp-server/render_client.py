"""Async HTTP client for Render API with retry logic and rate limiting"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiohttp
from config import settings

logger = logging.getLogger(__name__)

async def get_session():
    """Create a new HTTP client session for each request"""
    timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
    headers = {
        "Authorization": f"Bearer {settings.RENDER_API_KEY}",
        "Content-Type": "application/json"
    }

    return aiohttp.ClientSession(
        base_url=settings.RENDER_BASE_URL,
        headers=headers,
        timeout=timeout
    )


async def make_request_with_retry(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = None
) -> Dict[str, Any]:
    """
    Make HTTP request with exponential backoff retry logic for rate limiting

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        params: Query parameters
        max_retries: Override default retry count

    Returns:
        JSON response data

    Raises:
        RuntimeError: For API errors or too many retries
    """
    max_retries = max_retries or settings.MAX_RETRIES
    retry_count = 0
    delay = 1

    while retry_count < max_retries:
        session = None
        try:
            session = await get_session()
            async with session.request(method, endpoint, params=params) as response:
                # Handle rate limiting (429)
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", delay))
                    logger.warning(f"⚠️ Rate limited (429). Waiting {retry_after}s before retry {retry_count + 1}/{max_retries}")
                    await asyncio.sleep(retry_after)
                    delay *= 2  # Exponential backoff
                    retry_count += 1
                    continue

                # Handle other HTTP errors
                if not response.ok:
                    error_text = await response.text()
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get('error', error_data.get('message', error_text))
                    except:
                        error_msg = error_text

                    raise RuntimeError(f"Render API error {response.status}: {error_msg}")

                # Success - return JSON data
                result = await response.json()
                return result

        except aiohttp.ClientError as e:
            logger.error(f"❌ HTTP client error: {e}")
            if retry_count == max_retries - 1:
                raise RuntimeError(f"HTTP request failed after {max_retries} retries: {e}")

            await asyncio.sleep(delay)
            delay *= 2
            retry_count += 1

        finally:
            if session:
                await session.close()

    raise RuntimeError(f"Too many retries ({max_retries}) - circuit breaker tripped")


async def get_logs(
    service_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = None,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch logs for a service with pagination support

    Args:
        service_id: Render service ID
        start_time: ISO timestamp for log start
        end_time: ISO timestamp for log end
        limit: Max logs per request
        cursor: Pagination cursor

    Returns:
        Dict with 'logs', 'cursor', 'hasMore' fields
    """
    params = {}

    if start_time:
        params['start'] = start_time
    if end_time:
        params['end'] = end_time
    if limit:
        params['limit'] = min(limit, settings.MAX_LOGS_PER_REQUEST)
    if cursor:
        params['cursor'] = cursor

    # Use the global logs endpoint with service filtering
    params['serviceIds'] = service_id
    endpoint = "logs"
    return await make_request_with_retry("GET", endpoint, params)


async def get_deployments(service_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Fetch deployment history for a service

    Args:
        service_id: Render service ID
        limit: Max deployments to return

    Returns:
        Dict with deployment data
    """
    params = {"limit": min(limit, 100)}
    endpoint = f"services/{service_id}/deploys"
    return await make_request_with_retry("GET", endpoint, params)


async def get_service_status(service_id: str) -> Dict[str, Any]:
    """
    Get current service status and basic info

    Args:
        service_id: Render service ID

    Returns:
        Dict with service status data
    """
    endpoint = f"services/{service_id}"
    return await make_request_with_retry("GET", endpoint)


async def get_metrics(
    service_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch service metrics (CPU, memory, etc.)

    Args:
        service_id: Render service ID
        start_time: ISO timestamp for metrics start
        end_time: ISO timestamp for metrics end

    Returns:
        Dict with metrics time series data
    """
    params = {}
    if start_time:
        params['start'] = start_time
    if end_time:
        params['end'] = end_time

    # Check if metrics endpoint exists, use general endpoint if needed
    endpoint = f"services/{service_id}/metrics"
    return await make_request_with_retry("GET", endpoint, params)