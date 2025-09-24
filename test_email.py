#!/usr/bin/env python3
"""
Test email functionality with Gmail app password
"""

import asyncio
import os
from surf_lamp_insights import SurfLampInsights

async def main():
    print("📧 Testing email system...")

    # You MUST replace this with your actual Gmail app password
    app_password = input("Enter your Gmail app password (create one at https://myaccount.google.com/apppasswords): ").strip()

    if not app_password:
        print("❌ No password provided, skipping email test")
        return

    # Set the password temporarily
    os.environ['EMAIL_PASSWORD'] = app_password

    insights_generator = SurfLampInsights()

    # Test sending a simple email
    success = insights_generator.send_email(
        subject="Test - Surf Lamp Monitoring Setup",
        body="""✅ Your Surf Lamp monitoring system is now configured!

This is a test email to confirm email delivery is working.

📊 Features enabled:
- Every 2 hours: Alert checks for critical issues
- Daily at 8:00 AM: Full AI insights report
- Immediate alerts: When error count > 5

System is ready for automated monitoring!
""",
        is_alert=False
    )

    if success:
        print("✅ Test email sent successfully!")
        print("📧 Check your inbox at shaharisn1@gmail.com")
    else:
        print("❌ Email test failed - check your app password")

if __name__ == "__main__":
    asyncio.run(main())