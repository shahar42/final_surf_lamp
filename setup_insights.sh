#!/bin/bash
"""
Surf Lamp AI Insights Setup Script
Sets up daily AI-powered insights generation using OpenAI and MCP server data
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSIGHTS_SCRIPT="$SCRIPT_DIR/surf_lamp_insights.py"

echo "🧠 Setting up Surf Lamp AI Insights System..."

# Check if insights script exists
if [ ! -f "$INSIGHTS_SCRIPT" ]; then
    echo "❌ Insights script not found: $INSIGHTS_SCRIPT"
    exit 1
fi

# Make script executable
chmod +x "$INSIGHTS_SCRIPT"

# Check for OpenAI API key
if [ ! -f "$SCRIPT_DIR/.env" ] || ! grep -q "OPENAI_API_KEY" "$SCRIPT_DIR/.env"; then
    echo "⚠️ OpenAI API key not configured"
    echo "📝 Please:"
    echo "   1. Copy insights_config.env to .env"
    echo "   2. Add your OpenAI API key to .env"
    echo "   3. Set INSIGHTS_ENABLED=true"
    echo ""
    echo "💡 Get API key from: https://platform.openai.com/api-keys"
    echo ""
fi

# Test the system
echo "🧪 Testing insights system..."

if python3 "$INSIGHTS_SCRIPT" --test 2>/dev/null | grep -q "insights_generated"; then
    echo "✅ Insights system test successful!"
else
    echo "⚠️ Insights test may have issues - check configuration"
fi

echo ""
echo "📋 Setup daily scheduling?"
echo "1) Add to cron (8 AM daily)"
echo "2) Manual running only"
echo "3) Skip for now"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "⚙️ Setting up daily cron job..."

        # Create insights cron job (8 AM daily)
        CRON_JOB="0 8 * * * cd $SCRIPT_DIR && /usr/bin/python3 $INSIGHTS_SCRIPT >> logs/insights.log 2>&1"

        # Check if cron job already exists
        if crontab -l 2>/dev/null | grep -q "surf_lamp_insights.py"; then
            echo "⚠️ Insights cron job already exists"
        else
            # Add new cron job
            mkdir -p "$SCRIPT_DIR/logs"
            (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
            echo "✅ Daily insights cron job installed!"
        fi

        echo "🔍 Insights will run daily at 8 AM"
        echo "📋 View logs with: tail -f logs/insights.log"
        ;;

    2)
        echo "📝 Manual setup completed"
        ;;

    3)
        echo "⏭️ Skipping scheduling setup"
        ;;

    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🧠 AI Insights Commands:"
echo "  Test now:           python3 $INSIGHTS_SCRIPT --test"
echo "  Generate insights:  python3 $INSIGHTS_SCRIPT"
echo "  View results:       ls -la surf_lamp_insights_*.md"
echo ""
echo "📊 What the AI analyzes:"
echo "  • Performance patterns and bottlenecks"
echo "  • Error correlations and root causes"
echo "  • API usage patterns and optimization opportunities"
echo "  • Processing cycle health and timing"
echo "  • Predictive warnings based on trends"
echo ""
echo "💡 Pro tip: Run manually first to see sample insights!"
echo ""
echo "✅ AI Insights system setup complete!"