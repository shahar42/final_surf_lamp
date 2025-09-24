#!/bin/bash
"""
Setup cron jobs for Surf Lamp automated monitoring
- Alert checks every 2 hours
- Daily insights at 8:00 AM
"""

echo "🕒 Setting up Surf Lamp monitoring cron jobs..."

# Get current directory
SURF_LAMP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Surf Lamp directory: $SURF_LAMP_DIR"

# Create temporary cron file
TEMP_CRON_FILE="/tmp/surf_lamp_cron.tmp"

# Get existing cron jobs (if any)
crontab -l 2>/dev/null > "$TEMP_CRON_FILE"

# Remove any existing surf lamp entries
sed -i '/surf.lamp/d' "$TEMP_CRON_FILE" 2>/dev/null || true
sed -i '/run_alert_check/d' "$TEMP_CRON_FILE" 2>/dev/null || true
sed -i '/run_daily_insights/d' "$TEMP_CRON_FILE" 2>/dev/null || true

# Add new cron jobs
echo "" >> "$TEMP_CRON_FILE"
echo "# Surf Lamp automated monitoring" >> "$TEMP_CRON_FILE"
echo "# Alert checks every 2 hours" >> "$TEMP_CRON_FILE"
echo "0 */2 * * * cd $SURF_LAMP_DIR && python3 run_alert_check.py >> /tmp/surf_lamp_alerts.log 2>&1" >> "$TEMP_CRON_FILE"
echo "" >> "$TEMP_CRON_FILE"
echo "# Daily insights at 8:00 PM" >> "$TEMP_CRON_FILE"
echo "0 20 * * * cd $SURF_LAMP_DIR && python3 run_daily_insights.py >> /tmp/surf_lamp_insights.log 2>&1" >> "$TEMP_CRON_FILE"

# Install the cron jobs
crontab "$TEMP_CRON_FILE"

# Clean up
rm "$TEMP_CRON_FILE"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "📋 Scheduled jobs:"
echo "   • Alert checks: Every 2 hours (0 */2 * * *)"
echo "   • Daily insights: Daily at 8:00 AM (0 8 * * *)"
echo ""
echo "📝 Log files:"
echo "   • Alerts: /tmp/surf_lamp_alerts.log"
echo "   • Insights: /tmp/surf_lamp_insights.log"
echo ""
echo "🔍 To view current cron jobs: crontab -l"
echo "🗑️  To remove: crontab -e (then delete the surf lamp lines)"
echo ""
echo "⚠️  IMPORTANT: Make sure to set up your email credentials in .env file!"
echo "   - EMAIL_FROM=shaharisn1@gmail.com"
echo "   - EMAIL_PASSWORD=your-gmail-app-password"