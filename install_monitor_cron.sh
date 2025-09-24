#!/bin/bash
"""
Simple Cron-based Surf Lamp Monitor Installer
Sets up hourly health monitoring via cron job
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/surf_lamp_monitor.py"

echo "🚀 Installing Surf Lamp Health Monitor (Cron version)..."

# Make script executable
chmod +x "$MONITOR_SCRIPT"

# Create log directory
mkdir -p "$SCRIPT_DIR/logs"

# Add cron job (runs every hour)
CRON_JOB="0 * * * * cd $SCRIPT_DIR && /usr/bin/python3 $MONITOR_SCRIPT --test >> logs/monitor.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "surf_lamp_monitor.py"; then
    echo "⚠️ Surf Lamp monitor cron job already exists"
    echo "📋 Current cron jobs:"
    crontab -l | grep surf_lamp_monitor
else
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job installed successfully!"
fi

echo ""
echo "🔍 Monitor commands:"
echo "  Test now:    python3 $MONITOR_SCRIPT --test"
echo "  View logs:   tail -f logs/monitor.log"
echo "  Remove cron: crontab -e (then delete the surf_lamp_monitor line)"
echo ""
echo "📧 To enable alerts:"
echo "  1. Copy monitor_config.env to .env"
echo "  2. Edit .env and set ALERT_EMAIL_ENABLED=true"
echo "  3. Configure email settings in .env"
echo ""
echo "✅ Setup complete! Monitor will run every hour."