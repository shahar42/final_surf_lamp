# Render MCP Server

Real-time access to Render logs, deployments, and metrics for debugging the Surf Lamp background processor.

## 🚀 Setup

1. **Install dependencies:**
   ```bash
   cd render-mcp-server
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values:
   # RENDER_API_KEY=your_render_api_key_here
   # SERVICE_ID=your_surf_lamp_service_id
   ```

3. **Get your Render API key:**
   - Go to [Render Dashboard](https://dashboard.render.com/account)
   - Navigate to Account Settings
   - Generate a new API Key
   - Copy it to your `.env` file

4. **Find your Service ID:**
   - Go to your Surf Lamp service in Render
   - Look at the URL: `https://dashboard.render.com/web/srv-XXXXX`
   - The `srv-XXXXX` part is your SERVICE_ID

## 🔧 Claude Code Integration

Add this MCP server to your Claude Code configuration:

```bash
# Navigate to the render-mcp-server directory
cd /home/shahar42/Git_Surf_Lamp_Agent/render-mcp-server

# Test the server locally first
python main.py --test

# Add to Claude Code (adjust path as needed)
claude mcp add render-logs ./main.py --transport stdio
```

## 🎯 Available Tools

Once integrated, you can use these tools in Claude Code:

### 📋 Log Tools
- **`render_logs`** - Fetch filtered logs with time range and search
- **`search_render_logs`** - Search recent logs for specific text
- **`render_recent_errors`** - Find recent errors and warnings

### 🚀 Deployment Tools
- **`render_deployments`** - Get deployment history
- **`render_service_status`** - Current service status
- **`render_latest_deployment_logs`** - Logs from latest deployment

### 📊 Monitoring Tools
- **`render_metrics`** - Performance metrics (CPU, memory, requests)
- **`render_health_check`** - Complete health summary

## 💡 Usage Examples

```python
# Get recent logs with timeout errors
render_logs(search_text="timeout", hours_back=2)

# Check if latest deployment succeeded
render_latest_deployment_logs()

# Monitor performance during high load
render_metrics(hours_back=1)

# Search for OpenWeatherMap API issues
search_render_logs("OpenWeatherMap", hours_back=6)

# Get complete health overview
render_health_check()
```

## 🔍 Debugging the Surf Lamp System

This MCP server is specifically designed to debug production issues like:

- **Timeout errors** in OpenWeatherMap API calls
- **Rate limiting** issues (429 errors)
- **Background processor crashes**
- **Deployment failures**
- **Performance bottlenecks**

Example debugging workflow:
1. `render_health_check()` - Get overall system status
2. `render_recent_errors()` - Find recent issues
3. `search_render_logs("timeout")` - Look for specific problems
4. `render_metrics()` - Check performance impact

## ⚠️ Security Notes

- Keep your `.env` file private (it's in `.gitignore`)
- API keys provide full access to your Render account
- This server runs locally and connects directly to Render's API
- All communication with Claude happens through stdio (no network exposure)

## 🛠️ Troubleshooting

**"Module not found" errors:**
```bash
pip install -r requirements.txt
```

**"API key invalid" errors:**
- Check your `.env` file has the correct `RENDER_API_KEY`
- Verify the API key in Render Dashboard

**"Service not found" errors:**
- Verify `SERVICE_ID` in `.env` matches your actual service ID
- Check the service ID format (should be `srv-xxxxx`)

**Rate limiting (429 errors):**
- The server has built-in retry logic with exponential backoff
- If you hit limits frequently, reduce query frequency

## 📝 Configuration

The server uses these environment variables:

```bash
# Required
RENDER_API_KEY=your_api_key_here
SERVICE_ID=srv-your_service_id

# Optional (with defaults)
RENDER_BASE_URL=https://api.render.com/v1
MAX_LOGS_PER_REQUEST=100
MAX_TOTAL_LOGS=1000
REQUEST_TIMEOUT=30
MAX_RETRIES=5
```