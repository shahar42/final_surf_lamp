#!/bin/bash
"""
Surf Lamp Monitoring Setup Script
Sets up automated hourly health monitoring with multiple scheduling options
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/surf_lamp_monitor.py"
SERVICE_NAME="surf-lamp-monitor"

echo "🚀 Setting up Surf Lamp Health Monitoring..."

# Check if monitor script exists
if [ ! -f "$MONITOR_SCRIPT" ]; then
    echo "❌ Monitor script not found: $MONITOR_SCRIPT"
    exit 1
fi

# Make monitor script executable
chmod +x "$MONITOR_SCRIPT"

echo "📋 Choose monitoring setup method:"
echo "1) Systemd timer (recommended for servers)"
echo "2) Cron job (traditional)"
echo "3) Manual running only"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "⚙️ Setting up systemd timer..."

        # Create systemd service file
        sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=Surf Lamp Health Monitor
After=network.target

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $MONITOR_SCRIPT --test
Environment=PATH=/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

        # Create systemd timer file
        sudo tee "/etc/systemd/system/${SERVICE_NAME}.timer" > /dev/null <<EOF
[Unit]
Description=Run Surf Lamp Health Monitor every hour
Requires=${SERVICE_NAME}.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

        # Reload systemd and enable timer
        sudo systemctl daemon-reload
        sudo systemctl enable "${SERVICE_NAME}.timer"
        sudo systemctl start "${SERVICE_NAME}.timer"

        echo "✅ Systemd timer installed and started"
        echo "🔍 Check status with: sudo systemctl status ${SERVICE_NAME}.timer"
        echo "📋 View logs with: sudo journalctl -u ${SERVICE_NAME}.service -f"
        ;;

    2)
        echo "⚙️ Setting up cron job..."

        # Add cron job
        (crontab -l 2>/dev/null; echo "0 * * * * cd $SCRIPT_DIR && /usr/bin/python3 $MONITOR_SCRIPT --test >> surf_lamp_monitor.log 2>&1") | crontab -

        echo "✅ Cron job installed (runs every hour)"
        echo "🔍 Check with: crontab -l"
        echo "📋 View logs with: tail -f $SCRIPT_DIR/surf_lamp_monitor.log"
        ;;

    3)
        echo "📝 Manual setup completed"
        echo "🔍 Test with: python3 $MONITOR_SCRIPT --test"
        echo "🚀 Run continuously with: python3 $MONITOR_SCRIPT"
        ;;

    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📧 Alert Configuration:"
echo "1. Copy monitor_config.env to .env and configure alerts"
echo "2. Set ALERT_EMAIL_ENABLED=true and email settings for email alerts"
echo "3. Set ALERT_DISCORD_ENABLED=true and webhook URL for Discord alerts"
echo ""
echo "🧪 Test the monitoring:"
echo "   python3 $MONITOR_SCRIPT --test"
echo ""
echo "✅ Surf Lamp monitoring setup complete!"