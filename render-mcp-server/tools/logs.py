"""MCP tools for Render logs"""

import json
from typing import Optional
from datetime import datetime, timedelta
from config import settings
import render_client


async def get_render_logs(
    service_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 50,
    search_text: Optional[str] = None
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
    try:
        # Use configured service ID if not provided
        target_service_id = service_id or settings.SERVICE_ID

        # Set reasonable defaults for time range if not provided
        if not start_time and not end_time:
            # Default to last 2 hours
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=2)
            start_time = start_dt.isoformat() + 'Z'
            end_time = end_dt.isoformat() + 'Z'

        # Collect all logs with pagination
        all_logs = []
        cursor = None
        total_fetched = 0
        max_total = min(limit, settings.MAX_TOTAL_LOGS)

        while total_fetched < max_total:
            remaining = max_total - total_fetched
            page_limit = min(remaining, settings.MAX_LOGS_PER_REQUEST)

            response = await render_client.get_logs(
                service_id=target_service_id,
                start_time=start_time,
                end_time=end_time,
                limit=page_limit,
                cursor=cursor
            )

            logs = response.get('logs', [])
            if not logs:
                break

            # Filter by search text if provided
            if search_text:
                logs = [log for log in logs if search_text.lower() in log.get('message', '').lower()]

            all_logs.extend(logs)
            total_fetched += len(logs)

            # Check for more pages
            cursor = response.get('cursor')
            if not cursor or not response.get('hasMore', False):
                break

        # Format output for Claude
        if not all_logs:
            return f"No logs found for service {target_service_id} in the specified time range."

        # Format logs in a readable way
        formatted_logs = []
        formatted_logs.append(f"🔍 Render Logs for Service: {target_service_id}")
        formatted_logs.append(f"📅 Time Range: {start_time} to {end_time}")
        formatted_logs.append(f"📊 Found {len(all_logs)} logs")

        if search_text:
            formatted_logs.append(f"🔎 Filtered by: '{search_text}'")

        formatted_logs.append("\n" + "="*80 + "\n")

        for i, log in enumerate(all_logs, 1):
            timestamp = log.get('timestamp', 'Unknown')
            message = log.get('message', 'No message')
            level = log.get('level', 'INFO')

            # Truncate very long messages
            if len(message) > 500:
                message = message[:497] + "..."

            formatted_logs.append(f"[{i:03d}] {timestamp} [{level}] {message}")

        # Add truncation notice if needed
        if len(all_logs) >= max_total:
            formatted_logs.append(f"\n⚠️ Output truncated to {max_total} logs. Use time filters for more specific results.")

        return "\n".join(formatted_logs)

    except Exception as e:
        return f"❌ Error fetching logs: {str(e)}"


async def search_logs(
    search_text: str,
    hours_back: int = 2,
    service_id: Optional[str] = None
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
    try:
        # Calculate time range
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(hours=hours_back)
        start_time = start_dt.isoformat() + 'Z'
        end_time = end_dt.isoformat() + 'Z'

        return await get_render_logs(
            service_id=service_id,
            start_time=start_time,
            end_time=end_time,
            limit=200,
            search_text=search_text
        )

    except Exception as e:
        return f"❌ Error searching logs: {str(e)}"


async def get_recent_errors(
    hours_back: int = 6,
    service_id: Optional[str] = None
) -> str:
    """
    Get recent error and warning logs.

    Args:
        hours_back: How many hours back to search (default: 6)
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Recent error logs
    """
    try:
        # Search for common error patterns
        error_patterns = ["ERROR", "❌", "Exception", "Failed", "failed", "timeout", "429"]

        results = []
        for pattern in error_patterns[:3]:  # Limit to avoid too many requests
            logs = await search_logs(pattern, hours_back, service_id)
            if "Found 0 logs" not in logs:
                results.append(f"\n🔍 Searching for '{pattern}':\n{logs}")

        if not results:
            return f"✅ No recent errors found in the last {hours_back} hours"

        return "\n".join(results)

    except Exception as e:
        return f"❌ Error searching for errors: {str(e)}"