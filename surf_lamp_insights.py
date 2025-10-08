#!/usr/bin/env python3
"""
Surf Lamp AI Insights System
LLM-powered daily analytics and insights generation using MCP server data.

Collects comprehensive system data and uses AI to identify:
- Performance patterns and trends
- Error correlations and root causes
- Usage analytics and optimization opportunities
- Predictive warnings and recommendations
"""

import asyncio
import os
import sys
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from dataclasses import dataclass, asdict

# Add render-mcp-server to path
sys.path.append('./render-mcp-server')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("surf_lamp_insights.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("surf-insights")

@dataclass
class SystemSnapshot:
    """Structured data snapshot for LLM analysis"""
    timestamp: str
    timeframe: str

    # Service health data
    web_service_logs: List[str]
    background_service_logs: List[str]
    service_status: Dict
    recent_deployments: List[Dict]
    service_events: List[Dict]

    # Performance metrics
    error_summary: Dict
    api_activity: Dict
    processing_performance: Dict

    # Operational insights
    alert_history: List[Dict]
    system_health_trends: Dict

class SurfLampInsights:
    def __init__(self):
        self.load_config()
        self.setup_render_tools()
        self.setup_llm_client()

    def load_config(self):
        """Load configuration from environment"""
        # Load main environment first
        main_env_path = './.env'
        if os.path.exists(main_env_path):
            with open(main_env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        os.environ[key] = value

        # Load render MCP environment
        env_path = './render-mcp-server/.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        os.environ[key] = value

        # LLM configuration
        self.llm_provider = os.getenv('INSIGHTS_LLM_PROVIDER', 'gemini').lower()
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('INSIGHTS_MODEL', 'gemini-2.0-flash-exp')
        self.insights_enabled = os.getenv('INSIGHTS_ENABLED', 'false').lower() == 'true'

        # Analysis configuration
        self.lookback_hours = int(os.getenv('INSIGHTS_LOOKBACK_HOURS', '24'))
        self.analysis_depth = os.getenv('INSIGHTS_DEPTH', 'standard')  # basic, standard, deep
        self.analysis_only = os.getenv('INSIGHTS_ANALYSIS_ONLY', 'true').lower() == 'true'

        # Output configuration
        self.save_to_file = os.getenv('INSIGHTS_SAVE_FILE', 'true').lower() == 'true'
        self.output_format = os.getenv('INSIGHTS_OUTPUT_FORMAT', 'txt').lower()
        self.output_dir = os.getenv('INSIGHTS_OUTPUT_DIR', './insights')
        self.email_enabled = os.getenv('INSIGHTS_EMAIL', 'false').lower() == 'true'

        # Email configuration
        self.email_smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.email_smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.email_from = os.getenv('EMAIL_FROM', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        self.email_to = os.getenv('EMAIL_TO', '')

        # Alert configuration
        self.immediate_alerts = os.getenv('INSIGHTS_IMMEDIATE_ALERTS', 'false').lower() == 'true'
        self.alert_error_threshold = int(os.getenv('ALERT_ERROR_THRESHOLD', '5'))
        self.alert_response_time_ms = int(os.getenv('ALERT_RESPONSE_TIME_MS', '2000'))
        self.alert_downtime_minutes = int(os.getenv('ALERT_DOWNTIME_MINUTES', '5'))

    def setup_render_tools(self):
        """Import and setup render MCP tools"""
        try:
            from render_mcp_server import (
                render_logs,
                search_render_logs,
                render_recent_errors,
                render_service_status,
                render_deployments,
                render_service_events
            )
            self.render_logs = render_logs
            self.search_render_logs = search_render_logs
            self.render_recent_errors = render_recent_errors
            self.render_service_status = render_service_status
            self.render_deployments = render_deployments
            self.render_service_events = render_service_events
            logger.info("✅ Render MCP tools loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Render MCP tools: {e}")
            sys.exit(1)

    def setup_llm_client(self):
        """Setup LLM client (Gemini or OpenAI)"""
        self.llm_enabled = False

        if self.llm_provider == 'gemini':
            if not self.gemini_api_key:
                logger.warning("⚠️ GEMINI_API_KEY not found - LLM analysis disabled")
                return

            try:
                genai.configure(api_key=self.gemini_api_key)
                self.llm_client = genai.GenerativeModel(self.model)
                self.llm_enabled = True
                logger.info(f"✅ Gemini client configured with model {self.model}")
            except Exception as e:
                logger.error(f"❌ Failed to setup Gemini client: {e}")

        elif self.llm_provider == 'openai':
            if not self.openai_api_key:
                logger.warning("⚠️ OPENAI_API_KEY not found - LLM analysis disabled")
                return

            try:
                import openai
                openai.api_key = self.openai_api_key
                self.llm_enabled = True
                logger.info("✅ OpenAI client configured")
            except Exception as e:
                logger.error(f"❌ Failed to setup OpenAI client: {e}")

        else:
            logger.error(f"❌ Unknown LLM provider: {self.llm_provider}")

        # Create output directory
        if self.save_to_file:
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"📁 Output directory ready: {self.output_dir}")

    async def collect_system_data(self, hours: int = 24) -> SystemSnapshot:
        """Aggregate comprehensive system data for analysis"""
        logger.info(f"📊 Collecting {hours}h of system data...")

        try:
            # Calculate log limits based on timeframe
            log_limit = min(hours * 20, 500)  # ~20 logs per hour, max 500

            # Collect service logs
            logger.info("📋 Collecting service logs...")
            web_logs = await self.render_logs(service_id="final-surf-lamp-web", limit=log_limit)
            bg_logs = await self.render_logs(service_id="final-surf-lamp-worker", limit=log_limit)

            # Collect service status and events
            logger.info("⚙️ Collecting service status...")
            service_status = await self.render_service_status()
            deployments = await self.render_deployments(limit=10)
            events = await self.render_service_events(limit=20)

            # Analyze errors and patterns
            logger.info("🔍 Analyzing error patterns...")
            web_errors = await self.render_recent_errors(service_id="final-surf-lamp-web", limit=100)
            bg_errors = await self.render_recent_errors(service_id="final-surf-lamp-worker", limit=100)

            # Collect API activity data
            logger.info("🔌 Analyzing API activity...")
            arduino_activity = await self.search_render_logs("arduino", service_id="final-surf-lamp-web", limit=200)
            api_errors = await self.search_render_logs("400\\|500\\|error", service_id="final-surf-lamp-web", limit=50)

            # Performance analysis
            logger.info("📈 Analyzing performance...")
            processing_logs = await self.search_render_logs("CYCLE COMPLETED\\|Fetching surf data", service_id="final-surf-lamp-worker", limit=100)
            threshold_activity = await self.search_render_logs("threshold\\|Quiet hours", service_id="final-surf-lamp-web", limit=100)

            # Structure the data
            snapshot = SystemSnapshot(
                timestamp=datetime.now().isoformat(),
                timeframe=f"{hours} hours",

                # Raw logs (parsed into lines)
                web_service_logs=self._parse_log_lines(web_logs),
                background_service_logs=self._parse_log_lines(bg_logs),

                # Service data
                service_status=self._parse_service_status(service_status),
                recent_deployments=self._parse_deployments(deployments),
                service_events=self._parse_events(events),

                # Analysis summaries
                error_summary={
                    "web_errors": self._summarize_errors(web_errors),
                    "background_errors": self._summarize_errors(bg_errors)
                },
                api_activity={
                    "arduino_requests": self._analyze_api_activity(arduino_activity),
                    "error_patterns": self._analyze_api_errors(api_errors)
                },
                processing_performance=self._analyze_processing_performance(processing_logs),

                # Operational data
                alert_history=[],  # Could integrate with monitoring history
                system_health_trends=self._analyze_health_trends(threshold_activity)
            )

            logger.info("✅ Data collection complete")
            return snapshot

        except Exception as e:
            logger.error(f"❌ Data collection failed: {e}")
            raise

    def _parse_log_lines(self, log_text: str) -> List[str]:
        """Extract individual log lines from formatted log output"""
        if not log_text or log_text.startswith("❌"):
            return []

        lines = log_text.split('\n')
        # Skip header lines, extract actual log entries
        log_lines = []
        for line in lines:
            if line.strip() and ('|' in line or 'INFO:' in line or 'ERROR:' in line):
                log_lines.append(line.strip())

        return log_lines[-50:]  # Last 50 entries for analysis

    def _parse_service_status(self, status_text: str) -> Dict:
        """Extract key service status information"""
        status_data = {"status": "unknown", "details": {}}

        # Check for success/error indicators
        if "SUCCESS:" in status_text or "✅" in status_text:
            status_data["status"] = "healthy"
        elif "ERROR:" in status_text or "❌" in status_text or "FAILED" in status_text:
            status_data["status"] = "error"
        elif "INFO:" in status_text and "Type:" in status_text:
            # Has service info, assume operational
            status_data["status"] = "operational"

        # Extract key details
        lines = status_text.split('\n')
        for line in lines:
            if 'Type:' in line:
                status_data["details"]["type"] = line.split('Type:')[1].strip()
            elif 'URL:' in line:
                status_data["details"]["url"] = line.split('URL:')[1].strip()
            elif 'Instances:' in line:
                status_data["details"]["instances"] = line.split('Instances:')[1].strip()
            elif 'Plan:' in line:
                status_data["details"]["plan"] = line.split('Plan:')[1].strip()

        return status_data

    def _parse_deployments(self, deployments_text: str) -> List[Dict]:
        """Parse deployment information"""
        deployments = []
        if not deployments_text or deployments_text.startswith("❌"):
            return deployments

        lines = deployments_text.split('\n')
        current_deploy = {}

        for line in lines:
            if line.startswith('[') and ']' in line:
                if current_deploy:
                    deployments.append(current_deploy)
                current_deploy = {"entry": line.strip()}
            elif 'Status:' in line and current_deploy:
                current_deploy["status"] = line.split('Status:')[1].strip()
            elif 'Created:' in line and current_deploy:
                current_deploy["created"] = line.split('Created:')[1].strip()

        if current_deploy:
            deployments.append(current_deploy)

        return deployments[:5]  # Last 5 deployments

    def _parse_events(self, events_text: str) -> List[Dict]:
        """Parse service events"""
        events = []
        if not events_text or events_text.startswith("❌"):
            return events

        lines = events_text.split('\n')
        for line in lines:
            if line.startswith('[') and ']' in line:
                events.append({"event": line.strip()})

        return events[:10]  # Last 10 events

    def _summarize_errors(self, errors_text: str) -> Dict:
        """Summarize error patterns"""
        summary = {"count": 0, "types": [], "recent": []}

        if "Found" in errors_text and "errors/warnings" in errors_text:
            lines = errors_text.split('\n')
            for line in lines:
                if "Found" in line:
                    try:
                        count = int(line.split()[1])
                        summary["count"] = count
                    except:
                        pass
                elif line.startswith(('❌', '⚠️')):
                    summary["recent"].append(line.strip())

        return summary

    def _analyze_api_activity(self, api_logs: str) -> Dict:
        """Analyze Arduino API request patterns"""
        activity = {"total_requests": 0, "unique_devices": set(), "request_patterns": []}

        if not api_logs or api_logs.startswith("❌"):
            return activity

        lines = api_logs.split('\n')
        for line in lines:
            # Look for Arduino API requests in logs
            if '/arduino/' in line and ('GET' in line or 'requesting surf data' in line):
                activity["total_requests"] += 1
                # Extract Arduino ID from path or log message
                try:
                    if '/arduino/' in line:
                        arduino_id = line.split('/arduino/')[1].split('/')[0].split()[0]
                        activity["unique_devices"].add(arduino_id)
                except:
                    pass

        activity["unique_devices"] = list(activity["unique_devices"])
        return activity

    def _analyze_api_errors(self, error_logs: str) -> Dict:
        """Analyze API error patterns"""
        patterns = {"status_codes": {}, "error_types": []}

        if "Found" in error_logs:
            lines = error_logs.split('\n')
            for line in lines:
                if any(code in line for code in ['400', '404', '500', '502', '503']):
                    for code in ['400', '404', '500', '502', '503']:
                        if code in line:
                            patterns["status_codes"][code] = patterns["status_codes"].get(code, 0) + 1

        return patterns

    def _analyze_processing_performance(self, processing_logs: str) -> Dict:
        """Analyze background processing performance"""
        performance = {"cycle_times": [], "success_rate": 0, "avg_duration": 0}

        if processing_logs and not processing_logs.startswith("❌"):
            lines = processing_logs.split('\n')
            durations = []
            successes = 0
            total = 0

            for line in lines:
                # Look for actual success patterns in the logs
                if "LOCATION-BASED PROCESSING CYCLE COMPLETED" in line or "CYCLE COMPLETED" in line:
                    successes += 1
                    total += 1
                elif "Fetching surf data from:" in line or "Standardizing data from:" in line:
                    total += 1

                # Legacy duration parsing (keep for backward compatibility)
                if "Duration:" in line:
                    try:
                        duration_str = line.split("Duration:")[1].strip()
                        if "seconds" in duration_str:
                            duration = float(duration_str.split()[0])
                            durations.append(duration)
                    except:
                        pass

            if durations:
                performance["avg_duration"] = sum(durations) / len(durations)
                performance["cycle_times"] = durations[-10:]  # Last 10 cycles

            if total > 0:
                performance["success_rate"] = successes / total
            else:
                # If no processing logs found with old pattern, check for new pattern
                if "CYCLE COMPLETED" in processing_logs:
                    performance["success_rate"] = 1.0  # At least one successful cycle

        return performance

    def _analyze_health_trends(self, activity_logs: str) -> Dict:
        """Analyze system health trends"""
        trends = {"quiet_hours_active": 0, "threshold_alerts": 0, "locations": set()}

        if "Found" in activity_logs:
            lines = activity_logs.split('\n')
            for line in lines:
                if "Quiet hours active" in line:
                    trends["quiet_hours_active"] += 1
                    # Extract location
                    try:
                        location = line.split("for ")[1].split(" -")[0]
                        trends["locations"].add(location)
                    except:
                        pass
                elif "threshold" in line.lower() and "alert" in line.lower():
                    trends["threshold_alerts"] += 1

        trends["locations"] = list(trends["locations"])
        return trends

    async def generate_llm_insights(self, snapshot: SystemSnapshot) -> str:
        """Generate AI-powered insights from system data"""
        if not self.llm_enabled:
            return "LLM analysis disabled - API key not configured"

        logger.info(f"🧠 Generating LLM insights using {self.llm_provider}...")

        try:
            # Prepare structured data for LLM
            data_summary = {
                "timeframe": snapshot.timeframe,
                "service_status": snapshot.service_status,
                "error_summary": snapshot.error_summary,
                "api_activity": snapshot.api_activity,
                "processing_performance": snapshot.processing_performance,
                "health_trends": snapshot.system_health_trends,
                "recent_deployments": len(snapshot.recent_deployments),
                "recent_events": len(snapshot.service_events)
            }

            # Sample recent logs for context
            recent_logs_sample = {
                "web_logs": snapshot.web_service_logs[-10:],
                "background_logs": snapshot.background_service_logs[-10:]
            }

            prompt = f"""
You are an expert DevOps ANALYST for a surf lamp IoT system. Your role is STRICTLY READ-ONLY analysis and reporting.

CRITICAL CONSTRAINTS:
- Maximum 20 lines total output
- Be extremely concise - use bullet points
- Focus only on critical issues and key metrics
- No technical implementation details
- No code, SQL, or configuration suggestions

SYSTEM: IoT surf lamps serving Israeli beaches via web API + background weather processor

DATA SUMMARY:
{json.dumps(data_summary, indent=2)}

RECENT LOG SAMPLES:
{json.dumps(recent_logs_sample, indent=2)}

Provide ULTRA-CONCISE analysis (MAX 20 LINES):

System Health Summary
[2-3 lines: Current status, errors, uptime]

Performance Analysis
[2-3 lines: Key metrics, response times, throughput]

Notable Patterns
[2-3 lines: Unusual activity or trends]

Issues & Recommendations
[3-4 lines: Critical problems and high-level fixes needed]

Optimization Opportunities
[2-3 lines: Areas for improvement]

Trends & Predictions
[2-3 lines: What data suggests for future]

STRICT REQUIREMENT: Total output must NOT exceed 20 lines. Use bullet points. Be ruthlessly concise.
"""

            if self.llm_provider == 'gemini':
                # Use Gemini API
                response = self.llm_client.generate_content(prompt)
                insights = response.text
                logger.info("✅ Gemini insights generated successfully")

            elif self.llm_provider == 'openai':
                # Use OpenAI API
                import openai
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert DevOps engineer specializing in IoT systems and performance analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                insights = response.choices[0].message.content
                logger.info("✅ OpenAI insights generated successfully")

            else:
                return f"Error: Unknown LLM provider {self.llm_provider}"

            # Safety validation - ensure AI didn't provide code
            if self.analysis_only:
                insights = self._validate_analysis_only(insights)

            return insights

        except Exception as e:
            logger.error(f"❌ LLM insights generation failed: {e}")
            return f"Error generating insights: {str(e)}"

    def _validate_analysis_only(self, insights: str) -> str:
        """Validate that AI response contains only analysis, no code or technical solutions"""

        # Warning patterns that suggest code/implementation content (be specific to avoid false positives)
        warning_patterns = [
            'ALTER TABLE', 'CREATE TABLE', 'INSERT INTO', 'UPDATE SET', 'DELETE FROM',
            'def function', 'class Class', 'import sys', 'from datetime import', 'pip install',
            'apt-get install', 'sudo apt', 'npm install', 'yarn add', 'git commit',
            '```python', '```sql', '```javascript', '```bash', '```sh', '```json',
            'curl -X', 'wget http', 'docker run', 'docker build', 'systemctl restart',
            'service restart', 'crontab -e', 'export DATABASE_URL', 'source .env',
            'chmod +x', 'mkdir -p', 'rm -rf', 'mv file', 'cp file',
            'SELECT * FROM users', 'WHERE user_id', 'INNER JOIN', 'LEFT JOIN',
            'GROUP BY column', 'ORDER BY created', 'ADD COLUMN', 'DROP COLUMN'
        ]

        # Check for warning patterns
        insights_lower = insights.lower()
        detected_patterns = []

        for pattern in warning_patterns:
            if pattern.lower() in insights_lower:
                detected_patterns.append(pattern)

        if detected_patterns:
            logger.warning(f"⚠️ AI provided technical implementation details: {detected_patterns}")

            # Add warning to the insights
            warning_msg = f"""
⚠️ WARNING: This analysis contained technical implementation details which have been flagged.
The AI assistant should only provide observations and high-level recommendations, not code or specific technical solutions.
Detected patterns: {', '.join(detected_patterns)}

--- ORIGINAL ANALYSIS BELOW ---

"""
            insights = warning_msg + insights

        return insights

    def send_email(self, subject: str, body: str, is_alert: bool = False):
        """Send email notification"""
        if not self.email_enabled or not self.email_from or not self.email_password:
            logger.warning("Email configuration incomplete, skipping email")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = f"{'🚨 ALERT: ' if is_alert else '📊 '}{subject}"

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.email_smtp_server, self.email_smtp_port)
            server.starttls()
            server.login(self.email_from, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_from, self.email_to, text)
            server.quit()

            logger.info(f"✅ Email sent successfully: {subject}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False

    def check_for_alerts(self, snapshot: SystemSnapshot) -> List[str]:
        """Check system data for alert conditions"""
        alerts = []

        # Check error count
        total_errors = (snapshot.error_summary.get('web_errors', {}).get('count', 0) +
                       snapshot.error_summary.get('background_errors', {}).get('count', 0))
        if total_errors >= self.alert_error_threshold:
            alerts.append(f"🚨 High error count: {total_errors} errors in last {snapshot.timeframe}")

        # Check service status
        service_status = snapshot.service_status.get('status', '').lower()
        if 'suspended' in service_status or 'error' in service_status:
            alerts.append(f"🚨 Service status critical: {service_status}")

        # Check for deployment failures
        for deployment in snapshot.recent_deployments:
            if deployment.get('status') == 'build_failed' or deployment.get('status') == 'deploy_failed':
                alerts.append(f"🚨 Deployment failed: {deployment.get('commit_message', 'Unknown')}")

        return alerts

    def save_insights_report(self, snapshot: SystemSnapshot, insights: str):
        """Save insights report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"surf_lamp_insights_{timestamp}.{self.output_format}"
        filepath = os.path.join(self.output_dir, filename)

        if self.output_format == 'md':
            report = f"""# Surf Lamp System Insights Report
Generated: {snapshot.timestamp}
Analysis Period: {snapshot.timeframe}

## Raw Data Summary
- Web Service Logs: {len(snapshot.web_service_logs)} entries
- Background Service Logs: {len(snapshot.background_service_logs)} entries
- Service Status: {snapshot.service_status.get('status', 'unknown')}
- Recent Deployments: {len(snapshot.recent_deployments)}
- API Requests: {snapshot.api_activity.get('arduino_requests', {}).get('total_requests', 0)}
- Processing Avg Duration: {snapshot.processing_performance.get('avg_duration', 0):.1f}s

---

{insights}

---

## Technical Data Details
```json
{json.dumps(asdict(snapshot), indent=2)}
```
"""
        else:  # txt format
            report = f"""SURF LAMP SYSTEM INSIGHTS REPORT
Generated: {snapshot.timestamp}
Analysis Period: {snapshot.timeframe}

Raw Data Summary:
- Web Service Logs: {len(snapshot.web_service_logs)} entries
- Background Service Logs: {len(snapshot.background_service_logs)} entries
- Service Status: {snapshot.service_status.get('status', 'unknown')}
- Recent Deployments: {len(snapshot.recent_deployments)}
- API Requests: {snapshot.api_activity.get('arduino_requests', {}).get('total_requests', 0)}
- Processing Avg Duration: {snapshot.processing_performance.get('avg_duration', 0):.1f}s

{'-' * 80}

{insights}

{'-' * 80}

Technical Data Details:
{json.dumps(asdict(snapshot), indent=2)}
"""

        try:
            with open(filepath, 'w') as f:
                f.write(report)
            logger.info(f"📄 Insights report saved: {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save report: {e}")

    async def generate_daily_insights(self, is_alert_check: bool = False) -> Dict:
        """Main function to generate daily insights with email notifications"""
        logger.info("🚀 Starting insights generation...")

        try:
            # Collect system data
            snapshot = await self.collect_system_data(hours=self.lookback_hours)

            # Check for immediate alerts
            alerts = self.check_for_alerts(snapshot)

            # Send immediate alerts if any critical issues found
            if alerts and (self.immediate_alerts or is_alert_check):
                alert_body = f"""🚨 CRITICAL SYSTEM ALERTS DETECTED

Time: {snapshot.timestamp}
Analysis Period: {snapshot.timeframe}

ALERTS:
{''.join([f'- {alert}' + chr(10) for alert in alerts])}

Service Status: {snapshot.service_status.get('status', 'unknown')}
Total Errors: {snapshot.error_summary.get('web_errors', {}).get('count', 0) + snapshot.error_summary.get('background_errors', {}).get('count', 0)}

This is an automated alert from your Surf Lamp monitoring system.
"""

                self.send_email(
                    subject="Surf Lamp System Alert",
                    body=alert_body,
                    is_alert=True
                )

            # Generate LLM insights (skip for alert-only checks)
            llm_insights = ""
            if not is_alert_check:
                llm_insights = await self.generate_llm_insights(snapshot)

                # Save report
                if self.save_to_file:
                    self.save_insights_report(snapshot, llm_insights)

                # Send regular insights email
                if self.email_enabled and llm_insights:
                    insights_body = f"""📊 SURF LAMP SYSTEM INSIGHTS

Generated: {snapshot.timestamp}
Analysis Period: {snapshot.timeframe}

SUMMARY:
- Logs Analyzed: {len(snapshot.web_service_logs) + len(snapshot.background_service_logs)}
- Service Status: {snapshot.service_status.get('status', 'unknown')}
- Total Errors: {snapshot.error_summary.get('web_errors', {}).get('count', 0) + snapshot.error_summary.get('background_errors', {}).get('count', 0)}
- API Requests: {snapshot.api_activity.get('arduino_requests', {}).get('total_requests', 0)}

DETAILED INSIGHTS:
{llm_insights}

---
Automated insights from your Surf Lamp AI monitoring system.
"""

                    self.send_email(
                        subject=f"Surf Lamp Daily Insights - {datetime.now().strftime('%Y-%m-%d')}",
                        body=insights_body,
                        is_alert=False
                    )

            result = {
                "timestamp": snapshot.timestamp,
                "timeframe": snapshot.timeframe,
                "data_collected": True,
                "insights_generated": bool(llm_insights and not llm_insights.startswith("Error")),
                "insights": llm_insights,
                "alerts_found": len(alerts),
                "alerts": alerts,
                "summary": {
                    "total_logs": len(snapshot.web_service_logs) + len(snapshot.background_service_logs),
                    "service_status": snapshot.service_status.get('status'),
                    "error_count": snapshot.error_summary.get('web_errors', {}).get('count', 0) +
                                  snapshot.error_summary.get('background_errors', {}).get('count', 0),
                    "api_requests": snapshot.api_activity.get('arduino_requests', {}).get('total_requests', 0)
                }
            }

            logger.info("✅ Insights generation complete")
            return result

        except Exception as e:
            logger.error(f"❌ Insights generation failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "insights_generated": False,
                "alerts_found": 0
            }

async def main():
    """Main function for testing and running insights"""
    insights_generator = SurfLampInsights()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("🧪 Running test insights generation...")
        result = await insights_generator.generate_daily_insights()
        print(json.dumps(result, indent=2))
    else:
        # Could add scheduling logic here
        logger.info("📊 Generating daily insights...")
        result = await insights_generator.generate_daily_insights()

        if result.get('insights_generated'):
            print("✅ Daily insights generated successfully!")
            print(f"📄 Check the generated report file")
        else:
            print("❌ Insights generation failed")
            print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())