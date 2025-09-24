#!/usr/bin/env python3
"""
Render Background Worker Service for Surf Lamp Monitoring
Runs as a continuous service with scheduled insights and alert checks
"""

import asyncio
import os
import sys
import logging
import schedule
import time
from datetime import datetime
from surf_lamp_insights import SurfLampInsights

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("render-monitoring")

class RenderMonitoringService:
    def __init__(self):
        logger.info("🚀 Initializing Render Monitoring Service...")
        self.insights_generator = SurfLampInsights()
        self.running = True

        # Schedule jobs
        self.setup_schedule()
        logger.info("✅ Monitoring service initialized")

    def setup_schedule(self):
        """Setup scheduled jobs"""
        # Alert checks every 2 hours
        schedule.every(2).hours.do(self.run_alert_check)

        # Daily insights at 8:00 PM
        schedule.every().day.at("20:00").do(self.run_daily_insights)

        logger.info("📅 Scheduled jobs:")
        logger.info("   • Alert checks: Every 2 hours")
        logger.info("   • Daily insights: 8:00 PM daily")

    def run_alert_check(self):
        """Run alert check (non-blocking)"""
        logger.info("🚨 Running scheduled alert check...")
        try:
            result = asyncio.run(self.insights_generator.generate_daily_insights(is_alert_check=True))
            alerts_found = result.get('alerts_found', 0)

            if alerts_found > 0:
                logger.warning(f"⚠️  {alerts_found} alerts detected and sent")
                for alert in result.get('alerts', []):
                    logger.warning(f"   - {alert}")
            else:
                logger.info("✅ No critical issues detected")

            logger.info(f"📊 Status: {result.get('summary', {}).get('service_status', 'unknown')}")
            logger.info(f"🔍 Errors: {result.get('summary', {}).get('error_count', 0)}")

        except Exception as e:
            logger.error(f"❌ Alert check failed: {e}")

    def run_daily_insights(self):
        """Run daily insights generation (non-blocking)"""
        logger.info("📊 Running scheduled daily insights...")
        try:
            result = asyncio.run(self.insights_generator.generate_daily_insights(is_alert_check=False))

            if result.get('insights_generated'):
                logger.info("✅ Daily insights generated and emailed")
                logger.info(f"📊 Summary:")
                logger.info(f"   - Logs analyzed: {result.get('summary', {}).get('total_logs', 0)}")
                logger.info(f"   - Service status: {result.get('summary', {}).get('service_status', 'unknown')}")
                logger.info(f"   - Error count: {result.get('summary', {}).get('error_count', 0)}")

                alerts_found = result.get('alerts_found', 0)
                if alerts_found > 0:
                    logger.warning(f"⚠️  {alerts_found} alerts also detected in daily insights")
            else:
                logger.error("❌ Daily insights generation failed")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"❌ Daily insights failed: {e}")

    async def run_service(self):
        """Main service loop"""
        logger.info("🔄 Starting monitoring service loop...")

        while self.running:
            try:
                # Run pending scheduled jobs
                schedule.run_pending()

                # Sleep for 1 minute between checks
                await asyncio.sleep(60)

            except KeyboardInterrupt:
                logger.info("⏹️  Service interrupted by user")
                self.running = False
            except Exception as e:
                logger.error(f"❌ Service error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

        logger.info("🛑 Monitoring service stopped")

async def main():
    """Entry point for Render deployment"""
    logger.info("🚀 Starting Surf Lamp Monitoring Service on Render...")

    # Log environment info
    logger.info(f"🌍 Environment: {os.getenv('RENDER_SERVICE_NAME', 'local')}")
    logger.info(f"📧 Email enabled: {os.getenv('INSIGHTS_EMAIL', 'false')}")
    logger.info(f"🔑 Gemini API configured: {'✅' if os.getenv('GEMINI_API_KEY') else '❌'}")

    # Start the service
    service = RenderMonitoringService()
    await service.run_service()

if __name__ == "__main__":
    asyncio.run(main())