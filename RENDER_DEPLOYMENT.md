# 🚀 Deploy Surf Lamp Monitoring to Render

This guide shows how to deploy your automated monitoring system as a **Background Worker** service on Render.

## 📋 **Pre-Deployment Checklist**

### 1. **Gmail App Password** (Required)
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Create new app password for "Surf Lamp Monitoring"
3. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### 2. **Render API Key** (For MCP Integration)
1. Get from your Render dashboard → Account Settings → API Keys
2. Copy the `rnd_` prefixed key

## 🔧 **Deployment Steps**

### **Method 1: Using Render Dashboard (Recommended)**

1. **Create New Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository

2. **Configure Service**
   ```
   Name: surf-lamp-monitoring
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python render_monitoring_service.py
   Plan: Starter ($7/month)
   ```

3. **Add Environment Variables**
   ```bash
   # Required - Your API Keys
   GEMINI_API_KEY=AIzaSyCbDRTwx9KzSOdDdsuOy3ZPvFDlox0Z_S4
   EMAIL_PASSWORD=your-gmail-app-password-here
   RENDER_API_KEY=your-render-api-key-here

   # Email Configuration
   EMAIL_FROM=shaharisn1@gmail.com
   EMAIL_TO=shaharisn1@gmail.com
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587

   # Insights Configuration
   INSIGHTS_ENABLED=true
   INSIGHTS_EMAIL=true
   INSIGHTS_IMMEDIATE_ALERTS=true
   INSIGHTS_ANALYSIS_ONLY=true
   INSIGHTS_LOOKBACK_HOURS=24

   # Alert Thresholds
   ALERT_ERROR_THRESHOLD=5
   ALERT_RESPONSE_TIME_MS=2000
   ALERT_DOWNTIME_MINUTES=5

   # Optional
   PYTHON_VERSION=3.11.0
   ```

4. **Deploy**
   - Click "Create Background Worker"
   - Monitor deployment logs

### **Method 2: Using render.yaml (Auto-Deploy)**

1. **Push render.yaml to your repo**
   ```bash
   git add render.yaml
   git commit -m "Add Render monitoring service configuration"
   git push
   ```

2. **Create service from YAML**
   - In Render dashboard: "New +" → "Blueprint"
   - Select your repository
   - Render will auto-detect the `render.yaml`

3. **Add Secret Environment Variables** (not in YAML for security)
   - `GEMINI_API_KEY`: Your Gemini API key
   - `EMAIL_PASSWORD`: Your Gmail app password
   - `RENDER_API_KEY`: Your Render API key

## 📊 **What the Service Does**

### **🔄 Continuous Operation**
- Runs 24/7 as background worker
- No HTTP endpoints (pure monitoring service)
- Automatic restarts on failure

### **📅 Scheduled Operations**
- **Every 2 hours**: Alert checks
- **Daily at 8:00 AM**: Full AI insights
- **Immediate**: Critical issue alerts

### **📧 Email Notifications**
- 🚨 **Urgent alerts**: Sent immediately when issues detected
- 📊 **Daily insights**: Comprehensive reports sent every morning
- Both sent to: `shaharisn1@gmail.com`

## 🔍 **Monitoring the Service**

### **View Logs**
```bash
# In Render dashboard, go to your service → Logs
# Or use MCP tools:
python -c "
import asyncio
from render_mcp_server import render_logs
result = asyncio.run(render_logs(service_id='your-monitoring-service-id'))
print(result)
"
```

### **Service Health**
- Check "Events" tab in Render dashboard
- Monitor email delivery (you'll get daily confirmations)
- Watch for deployment success/failure

## 💰 **Cost**

- **Starter Plan**: $7/month
- **Free Tier**: 750 hours/month (31 days = 744 hours) - works too!
- **Resource Usage**: Very low (just scheduled tasks + API calls)

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **Email not sending**
   ```bash
   # Check environment variables in Render dashboard
   # Verify Gmail app password is correct
   # Check service logs for SMTP errors
   ```

2. **Gemini API errors**
   ```bash
   # Verify GEMINI_API_KEY is set correctly
   # Check API quota in Google Cloud Console
   ```

3. **Service crashes**
   ```bash
   # Check logs for Python import errors
   # Verify all requirements.txt dependencies
   ```

### **Test Deployment**
```bash
# Local test before deploying
python render_monitoring_service.py

# Should show:
# 🚀 Starting Surf Lamp Monitoring Service on Render...
# 📅 Scheduled jobs: Alert checks every 2 hours, Daily insights 8:00 AM
# 🔄 Starting monitoring service loop...
```

## ✅ **Benefits of Render Deployment**

1. **Always Running**: No dependency on your local machine
2. **Reliable**: Automatic restarts, monitoring
3. **Scalable**: Easy to adjust resources
4. **Integrated**: Works with your existing Render services
5. **Logs**: Centralized logging with your other services

Once deployed, you'll have a completely autonomous monitoring system running in the cloud!