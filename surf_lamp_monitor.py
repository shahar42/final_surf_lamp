#!/usr/bin/env python3
"""
Surf Lamp Health Monitor
Automated monitoring script that checks system health every hour and sends alerts when issues are detected.

Uses the Render MCP server tools to check:
- Service status (web + background)
- Recent errors in logs
- Processing cycles completion
- API response health
- Database connectivity

Sends alerts via email/SMS/Discord when issues are detected.
"""

import asyncio
import os
import sys
import json
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv not available, try manual loading
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    os.environ[key] = value

# Add render-mcp-server to path
sys.path.append('./render-mcp-server')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("surf_lamp_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("surf-monitor")

class SurfLampMonitor:
    def __init__(self):
        self.load_config()
        self.setup_render_tools()

    def load_config(self):
        """Load configuration from environment and config files"""
        # Load render MCP environment
        env_path = './render-mcp-server/.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value

        # Alert configuration
        self.email_enabled = os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
        self.discord_enabled = os.getenv('ALERT_DISCORD_ENABLED', 'false').lower() == 'true'

        # Email settings
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('ALERT_EMAIL_USER')
        self.email_password = os.getenv('ALERT_EMAIL_PASSWORD')
        self.alert_recipients = os.getenv('ALERT_RECIPIENTS', '').split(',')

        # Discord settings
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

        # Monitoring thresholds
        self.error_threshold = int(os.getenv('ERROR_THRESHOLD', '3'))  # Max errors per hour
        self.processing_timeout = int(os.getenv('PROCESSING_TIMEOUT', '90'))  # Max processing time in minutes

    def setup_render_tools(self):
        """Import render MCP tools"""
        try:
            from render_mcp_server import (
                render_logs,
                search_render_logs,
                render_recent_errors,
                render_service_status,
                render_deployments
            )
            self.render_logs = render_logs
            self.search_render_logs = search_render_logs
            self.render_recent_errors = render_recent_errors
            self.render_service_status = render_service_status
            self.render_deployments = render_deployments
            logger.info("✅ Render MCP tools loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Render MCP tools: {e}")
            sys.exit(1)

    async def check_service_health(self) -> Tuple[str, List[str]]:
        """Check if both services are running and healthy"""
        issues = []

        try:
            # Check web service status
            web_status = await self.render_service_status()
            if "❌" in web_status:
                issues.append("🌐 Web service status check failed")
            elif "✅" not in web_status:
                issues.append("🌐 Web service appears unhealthy")

            # Check recent deployments for failures
            deployments = await self.render_deployments(limit=3)
            if "build_failed" in deployments or "pre_deploy_failed" in deployments:
                issues.append("🚀 Recent deployment failures detected")

        except Exception as e:
            issues.append(f"🔧 Service health check failed: {str(e)}")

        status = "🔴 CRITICAL" if issues else "🟢 HEALTHY"
        return status, issues

    async def check_recent_errors(self) -> Tuple[str, List[str]]:
        """Check for recent errors in both services"""
        issues = []

        try:
            # Check web service errors
            web_errors = await self.render_recent_errors(limit=50, service_type="web")
            if "Found" in web_errors and "errors/warnings" in web_errors:
                # Extract error count
                if "Found" in web_errors:
                    lines = web_errors.split('\n')
                    for line in lines:
                        if "Found" in line and "errors/warnings" in line:
                            try:
                                error_count = int(line.split()[1])
                                if error_count > self.error_threshold:
                                    issues.append(f"🌐 Web service: {error_count} errors/warnings in recent logs")
                            except:
                                pass

            # Check background service errors
            bg_errors = await self.render_recent_errors(limit=50, service_type="background")
            if "Found" in bg_errors and "errors/warnings" in bg_errors:
                lines = bg_errors.split('\n')
                for line in lines:
                    if "Found" in line and "errors/warnings" in line:
                        try:
                            error_count = int(line.split()[1])
                            if error_count > self.error_threshold:
                                issues.append(f"🔧 Background service: {error_count} errors/warnings in recent logs")
                        except:
                            pass

        except Exception as e:
            issues.append(f"📋 Error log check failed: {str(e)}")

        if issues:
            status = "🔴 CRITICAL" if any("error" in issue.lower() for issue in issues) else "🟡 WARNING"
        else:
            status = "🟢 HEALTHY"

        return status, issues

    async def check_processing_cycles(self) -> Tuple[str, List[str]]:
        """Check if background processing is completing successfully"""
        issues = []

        try:
            # Get recent background service logs
            bg_logs = await self.render_logs(limit=20, service_type="background")

            # Look for successful processing completion
            if "Status: SUCCESS" not in bg_logs:
                issues.append("🔧 No successful processing cycles found in recent logs")

            # Check for timeout/stuck processing
            if "Duration:" in bg_logs:
                lines = bg_logs.split('\n')
                for line in lines:
                    if "Duration:" in line:
                        try:
                            duration_str = line.split("Duration:")[1].strip()
                            if "seconds" in duration_str:
                                duration = float(duration_str.split()[0])
                                if duration > (self.processing_timeout * 60):
                                    issues.append(f"🔧 Processing cycle too slow: {duration:.1f}s")
                        except:
                            pass

        except Exception as e:
            issues.append(f"🔄 Processing cycle check failed: {str(e)}")

        status = "🔴 CRITICAL" if issues else "🟢 HEALTHY"
        return status, issues

    async def check_api_responses(self) -> Tuple[str, List[str]]:
        """Check if Arduino API endpoints are responding"""
        issues = []

        try:
            # Search for recent Arduino API calls in web service logs
            api_logs = await self.search_render_logs("arduino", limit=20, service_type="web")

            if "No logs found" in api_logs:
                issues.append("🤖 No recent Arduino API activity detected")
            else:
                # Check for API errors
                error_api_logs = await self.search_render_logs("400\\|500\\|error", limit=10, service_type="web")
                if "Found" in error_api_logs:
                    issues.append("🤖 API errors detected in recent requests")

        except Exception as e:
            issues.append(f"🔌 API response check failed: {str(e)}")

        status = "🟡 WARNING" if issues else "🟢 HEALTHY"
        return status, issues

    async def check_database_connectivity(self) -> Tuple[str, List[str]]:
        """Check for database connection issues"""
        issues = []

        try:
            # Search for database-related errors
            db_errors = await self.search_render_logs("database\\|psycopg2\\|connection", limit=30)

            if "Found" in db_errors and "entries matching" in db_errors:
                issues.append("🗄️ Database connection issues detected")

            # Check for specific database errors
            critical_db_errors = await self.search_render_logs("UndefinedColumn\\|OperationalError", limit=10)
            if "Found" in critical_db_errors:
                issues.append("🗄️ Critical database errors detected")

        except Exception as e:
            issues.append(f"🗄️ Database check failed: {str(e)}")

        status = "🔴 CRITICAL" if any("Critical" in issue for issue in issues) else "🟡 WARNING" if issues else "🟢 HEALTHY"
        return status, issues

    async def run_health_check(self) -> Dict:
        """Run comprehensive health check"""
        logger.info("🔍 Starting Surf Lamp health check...")

        checks = {
            "service_health": await self.check_service_health(),
            "recent_errors": await self.check_recent_errors(),
            "processing_cycles": await self.check_processing_cycles(),
            "api_responses": await self.check_api_responses(),
            "database_connectivity": await self.check_database_connectivity()
        }

        # Determine overall status
        statuses = [check[0] for check in checks.values()]
        if any("🔴 CRITICAL" in status for status in statuses):
            overall_status = "🔴 CRITICAL"
        elif any("🟡 WARNING" in status for status in statuses):
            overall_status = "🟡 WARNING"
        else:
            overall_status = "🟢 HEALTHY"

        # Collect all issues
        all_issues = []
        for check_name, (status, issues) in checks.items():
            if issues:
                all_issues.extend([f"**{check_name.replace('_', ' ').title()}**: {issue}" for issue in issues])

        result = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "checks": checks,
            "issues": all_issues,
            "summary": f"Health check completed: {overall_status}"
        }

        logger.info(f"🏥 Health check result: {overall_status}")
        return result

    def send_email_alert(self, health_result: Dict):
        """Send email alert for health issues"""
        if not self.email_enabled or not self.email_user:
            return

        try:
            subject = f"🚨 Surf Lamp Alert - {health_result['overall_status']}"

            body = f"""
Surf Lamp System Health Alert
Time: {health_result['timestamp']}
Status: {health_result['overall_status']}

Issues Detected:
{chr(10).join(health_result['issues']) if health_result['issues'] else 'No issues detected'}

Detailed Check Results:
"""
            for check_name, (status, issues) in health_result['checks'].items():
                body += f"\n{check_name.replace('_', ' ').title()}: {status}"
                if issues:
                    body += f"\n  - {chr(10).join(issues)}"

            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ', '.join(self.alert_recipients)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            logger.info("📧 Email alert sent successfully")

        except Exception as e:
            logger.error(f"❌ Failed to send email alert: {e}")

    def send_discord_alert(self, health_result: Dict):
        """Send Discord webhook alert"""
        if not self.discord_enabled or not self.discord_webhook:
            return

        try:
            color = {
                "🔴 CRITICAL": 0xFF0000,  # Red
                "🟡 WARNING": 0xFFFF00,   # Yellow
                "🟢 HEALTHY": 0x00FF00    # Green
            }.get(health_result['overall_status'], 0x808080)

            embed = {
                "title": f"Surf Lamp Health Report",
                "description": health_result['summary'],
                "color": color,
                "timestamp": health_result['timestamp'],
                "fields": []
            }

            if health_result['issues']:
                embed['fields'].append({
                    "name": "🚨 Issues Detected",
                    "value": '\n'.join(health_result['issues'][:10]),  # Limit to 10 issues
                    "inline": False
                })

            # Add check summaries
            for check_name, (status, issues) in health_result['checks'].items():
                embed['fields'].append({
                    "name": check_name.replace('_', ' ').title(),
                    "value": status,
                    "inline": True
                })

            payload = {"embeds": [embed]}

            response = requests.post(self.discord_webhook, json=payload)
            response.raise_for_status()

            logger.info("📱 Discord alert sent successfully")

        except Exception as e:
            logger.error(f"❌ Failed to send Discord alert: {e}")

    def should_send_alert(self, health_result: Dict) -> bool:
        """Determine if an alert should be sent based on status"""
        # Always alert on critical issues
        if "🔴 CRITICAL" in health_result['overall_status']:
            return True

        # Alert on warnings (but could add logic to reduce noise)
        if "🟡 WARNING" in health_result['overall_status']:
            return True

        # Optional: Send "all clear" notifications after issues are resolved
        # return False  # Uncomment to disable "healthy" notifications

        return False

    async def monitor_once(self):
        """Run one monitoring cycle"""
        try:
            health_result = await self.run_health_check()

            # Save result to log file
            with open('health_check_results.json', 'w') as f:
                json.dump(health_result, f, indent=2)

            # Send alerts if needed
            if self.should_send_alert(health_result):
                logger.info("🚨 Sending alerts...")
                self.send_email_alert(health_result)
                self.send_discord_alert(health_result)
            else:
                logger.info("✅ No alerts needed")

            return health_result

        except Exception as e:
            logger.error(f"❌ Monitor cycle failed: {e}")
            return None

async def main():
    """Main monitoring function"""
    monitor = SurfLampMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run once for testing
        logger.info("🧪 Running test monitoring cycle...")
        result = await monitor.monitor_once()
        if result:
            print(json.dumps(result, indent=2))
    else:
        # Continuous monitoring mode
        logger.info("🚀 Starting continuous Surf Lamp monitoring...")
        while True:
            try:
                await monitor.monitor_once()
                logger.info("😴 Sleeping for 1 hour...")
                await asyncio.sleep(3600)  # 1 hour
            except KeyboardInterrupt:
                logger.info("👋 Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                await asyncio.sleep(300)  # 5 minutes before retry

if __name__ == "__main__":
    asyncio.run(main())