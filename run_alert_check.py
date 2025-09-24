#!/usr/bin/env python3
"""
Alert-only check script for cron scheduling
Runs quick checks for critical issues and sends immediate alerts
"""

import asyncio
import os
from surf_lamp_insights import SurfLampInsights

async def main():
    """Run alert check only"""
    print("🚨 Running alert check...")

    insights_generator = SurfLampInsights()

    # Run alert check (no full insights generation)
    result = await insights_generator.generate_daily_insights(is_alert_check=True)

    alerts_found = result.get('alerts_found', 0)
    if alerts_found > 0:
        print(f"⚠️  {alerts_found} alerts found and sent")
        for alert in result.get('alerts', []):
            print(f"   - {alert}")
    else:
        print("✅ No critical issues detected")

    print(f"📊 Status: {result.get('summary', {}).get('service_status', 'unknown')}")
    print(f"🔍 Errors: {result.get('summary', {}).get('error_count', 0)}")

if __name__ == "__main__":
    asyncio.run(main())