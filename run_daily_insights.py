#!/usr/bin/env python3
"""
Daily insights script for cron scheduling
Generates full AI insights and sends comprehensive email
"""

import asyncio
import os
from surf_lamp_insights import SurfLampInsights

async def main():
    """Run daily insights generation"""
    print("📊 Running daily insights generation...")

    insights_generator = SurfLampInsights()

    # Generate full daily insights
    result = await insights_generator.generate_daily_insights(is_alert_check=False)

    if result.get('insights_generated'):
        print("✅ Daily insights generated successfully!")
        print(f"📄 Report saved to: {insights_generator.output_dir}/")
        print(f"📧 Email sent: {insights_generator.send_email}")
        print(f"📊 Summary:")
        print(f"   - Logs analyzed: {result.get('summary', {}).get('total_logs', 0)}")
        print(f"   - Service status: {result.get('summary', {}).get('service_status', 'unknown')}")
        print(f"   - Error count: {result.get('summary', {}).get('error_count', 0)}")
        print(f"   - API requests: {result.get('summary', {}).get('api_requests', 0)}")

        alerts_found = result.get('alerts_found', 0)
        if alerts_found > 0:
            print(f"⚠️  {alerts_found} alerts also detected:")
            for alert in result.get('alerts', []):
                print(f"   - {alert}")
    else:
        print("❌ Daily insights generation failed")
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())