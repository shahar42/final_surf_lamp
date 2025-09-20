"""MCP tools for Render service metrics"""

import json
from typing import Optional
from datetime import datetime, timedelta
from config import settings
import render_client


async def get_service_metrics(
    service_id: Optional[str] = None,
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
    try:
        target_service_id = service_id or settings.SERVICE_ID

        # Calculate time range
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(hours=hours_back)
        start_time = start_dt.isoformat() + 'Z'
        end_time = end_dt.isoformat() + 'Z'

        response = await render_client.get_metrics(
            service_id=target_service_id,
            start_time=start_time,
            end_time=end_time
        )

        if not response:
            return f"No metrics available for service {target_service_id}"

        # Format metrics summary
        formatted = []
        formatted.append(f"📊 Service Metrics: {target_service_id}")
        formatted.append(f"📅 Time Range: Last {hours_back} hour(s)")
        formatted.append("\n" + "="*60 + "\n")

        # Process different metric types
        metrics = response.get('metrics', {})

        # CPU Metrics
        cpu_data = metrics.get('cpu', [])
        if cpu_data:
            cpu_values = [point.get('value', 0) for point in cpu_data if point.get('value') is not None]
            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)
                max_cpu = max(cpu_values)
                formatted.append(f"🔧 CPU Usage:")
                formatted.append(f"   Average: {avg_cpu:.1f}%")
                formatted.append(f"   Peak: {max_cpu:.1f}%")
                formatted.append("")

        # Memory Metrics
        memory_data = metrics.get('memory', [])
        if memory_data:
            memory_values = [point.get('value', 0) for point in memory_data if point.get('value') is not None]
            if memory_values:
                avg_memory = sum(memory_values) / len(memory_values)
                max_memory = max(memory_values)
                formatted.append(f"💾 Memory Usage:")
                formatted.append(f"   Average: {avg_memory:.1f} MB")
                formatted.append(f"   Peak: {max_memory:.1f} MB")
                formatted.append("")

        # HTTP Request Metrics
        requests_data = metrics.get('requests', [])
        if requests_data:
            total_requests = sum(point.get('value', 0) for point in requests_data if point.get('value') is not None)
            formatted.append(f"🌐 HTTP Requests:")
            formatted.append(f"   Total: {total_requests}")
            formatted.append(f"   Average per minute: {total_requests / (hours_back * 60):.1f}")
            formatted.append("")

        # Response Time Metrics
        latency_data = metrics.get('latency', [])
        if latency_data:
            latency_values = [point.get('value', 0) for point in latency_data if point.get('value') is not None]
            if latency_values:
                avg_latency = sum(latency_values) / len(latency_values)
                max_latency = max(latency_values)
                formatted.append(f"⚡ Response Times:")
                formatted.append(f"   Average: {avg_latency:.0f}ms")
                formatted.append(f"   Peak: {max_latency:.0f}ms")
                formatted.append("")

        # Instance Count
        instances_data = metrics.get('instances', [])
        if instances_data:
            latest_instances = instances_data[-1].get('value', 0) if instances_data else 0
            formatted.append(f"🖥️ Active Instances: {latest_instances}")
            formatted.append("")

        if len(formatted) <= 4:  # Only headers, no actual metrics
            formatted.append("⚠️ No detailed metrics available for this time period")
            formatted.append("Note: Metrics may not be available for all service types")

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error fetching metrics: {str(e)}"


async def get_performance_summary(
    service_id: Optional[str] = None
) -> str:
    """
    Get a quick performance health check for the service.

    Args:
        service_id: Render service ID (defaults to configured SERVICE_ID)

    Returns:
        Performance health summary
    """
    try:
        target_service_id = service_id or settings.SERVICE_ID

        # Get metrics for last hour for health check
        metrics_result = await get_service_metrics(target_service_id, hours_back=1)

        # Also get current service status
        from .deployments import get_service_status
        status_result = await get_service_status(target_service_id)

        # Combine for health summary
        formatted = []
        formatted.append(f"🏥 Performance Health Check: {target_service_id}")
        formatted.append("\n" + "="*50)
        formatted.append("\n🎯 Service Status:")
        formatted.append(status_result)
        formatted.append("\n🎯 Recent Performance:")
        formatted.append(metrics_result)

        return "\n".join(formatted)

    except Exception as e:
        return f"❌ Error generating performance summary: {str(e)}"