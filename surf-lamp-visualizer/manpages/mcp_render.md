# MCP Render

## 1. Overview

**What it does:** This server acts as a comprehensive production monitoring and deployment interface that allows maintainers to interact with Render services using natural language through Claude Code.

**Why it exists:** To make production debugging, monitoring, and deployment management easier by providing AI-powered access to Render's API. Eliminates manual dashboard navigation and enables rapid incident response through conversational commands.

---

## 2. Technical Details

**What would break if this disappeared?**
- Would be significantly harder to debug production issues in real-time
- Deployment monitoring and log analysis would require manual dashboard access
- Service health checks and performance monitoring would be slower
- Creating and managing Render services would require manual API calls or dashboard clicks

**What assumptions does it make?**
- **Environment:** Assumes `RENDER_API_KEY` and `OWNER_ID` are present and correct in its environment to connect to Render.
- **API Stability:** Expects Render API response formats to remain consistent (especially log entries, deployment objects, and service details structures).
- **Network:** Assumes reliable network connectivity to Render API (`https://api.render.com`).
- **Client:** Assumes it is being called by an MCP-compatible client (Claude Code) that understands how to format tool-use requests.
- **Service IDs:** Can work with both service names (e.g., "final-surf-lamp-web") and service IDs (e.g., "srv-xxx"), with intelligent fallback to default services.

**Where does complexity hide?**
- **Service Name Resolution:** The `get_service_id()` function automatically resolves service names to IDs using a cached services list, allowing users to refer to services by name instead of cryptic IDs. Fallback logic selects the first web service if no ID is provided.
- **Curl-Based HTTP Calls:** Uses subprocess `asyncio.create_subprocess_exec` to run `curl` commands instead of HTTP libraries. The `run_curl()` function parses HTTP status codes from curl's `-w "%{http_code}"` flag by extracting the last 3 characters of output.
- **Response Format Variation:** Different Render API endpoints wrap responses differently (some use `{"service": {...}}`, others return arrays, some have `{"deploys": [...]}` wrappers). The `_parse_service_data()` function normalizes these variations.
- **Intelligent Analysis Tools:** Tools like `render_service_events()` don't just return raw data - they analyze patterns (failed deployments, health issues) and provide actionable recommendations. This LLM-friendly format reduces cognitive load.
- **Dual Service Type Support:** Log tools accept a `service_type` parameter ("web" or "background") to automatically select the correct service when no ID is specified, preventing ambiguity in multi-service setups.
- **Deployment Validation:** The `validate_service_commands()` function checks for common deployment mistakes (local paths, missing dependencies) and provides git workflow reminders before service creation.

---

## 3. Architecture & Implementation

**How does data flow through this component?**
1. Claude Code (MCP Client) sends a JSON-RPC request to the server, specifying a tool and its parameters.
2. The `FastMCP` server routes the request to the appropriate async Python function (e.g., `@mcp.tool() async def render_logs()`).
3. The function resolves service names to IDs if needed using the cached services list.
4. It executes a `curl` command via `run_curl()` to hit the Render API with proper authentication headers.
5. The curl response (JSON body + HTTP status code) is parsed and validated.
6. Results are formatted into human-readable, LLM-friendly strings with semantic prefixes (ERROR:, SUCCESS:, WARNING:).
7. The formatted output is wrapped in a string and sent back to Claude as the tool's response.

**Key Functions/Classes:**
- `FastMCP("render")`: The MCP server instance.
- `run_curl()`: Core HTTP client that executes curl commands and parses responses (body + status code).
- `get_service_id()`: Resolves service names to IDs using cached services, with smart defaults.
- `fetch_all_services()`: Populates the global `SERVICES_CACHE` for name-to-ID lookups.
- `validate_service_commands()`: Validates deployment commands for common mistakes before service creation.
- `_parse_service_data()`: Normalizes service response formats and calculates derived data (costs, health status).
- `@mcp.tool()` decorated functions: Each function is a standalone capability exposed to Claude. They are organized by purpose:
    - **Deployment Monitoring:** `render_deployments`, `render_deploy_details`, `render_latest_deployment_logs`
    - **Service Health:** `render_service_status`, `render_service_events`, `render_services_status`
    - **Logs & Debugging:** `render_logs`, `search_render_logs`, `render_recent_errors`
    - **Service Management:** `render_restart_service`, `render_suspend_service`, `render_resume_service`, `render_scale_service`
    - **Configuration:** `render_environment_vars`, `render_get_custom_domains`, `render_get_secret_files`
    - **Resource Info:** `render_list_all_services`, `render_services_cost_analysis`, `render_services_ssh_info`
    - **Deployment Creation:** `create_web_service`, `create_background_worker`, `trigger_deploy` (from `deploy_tools.py`)

**Configuration:**
- The server is configured via two environment variables: `RENDER_API_KEY` and `OWNER_ID`.
- Default owner ID and API key are hardcoded in `deploy_tools.py` for deployment commands.

---

## 4. Integration Points

**What calls this component?**
- Claude Code via MCP protocol (stdio transport for local development).
- Any AI agent acting as an MCP client that supports the FastMCP protocol.

**What does this component call?**
- Render REST API (`https://api.render.com/v1/*`) via curl subprocess calls.
- `deploy_tools.py` module for service creation and deployment tools (uses aiohttp instead of curl).

**Data Formats/Contracts:**
- **Ingress:** Standard JSON-RPC 2.0 requests from the MCP client.
- **Egress:** Human-readable formatted strings with semantic prefixes for LLM parsing:
  - `ERROR:` - Errors that need attention
  - `SUCCESS:` - Successful operations
  - `WARNING:` - Warnings or degraded states
  - `INFO:` - Informational messages
  - `DEBUG:` - Debugging insights
  - `LIST:` - List-based outputs
  - `COST:` - Cost-related information
  - Timestamps are preserved from Render API (ISO 8601 UTC format).

---

## 5. Troubleshooting & Failure Modes

**How do you detect issues?**
- **Logs:** The server logs errors to `stderr`. Look for `asyncio.create_subprocess_exec` failures, curl errors, or Render API HTTP error codes (400s, 500s).
- **Claude Feedback:** Claude will report "ERROR:" prefixed messages when tools fail, with human-readable error descriptions.
- **Symptoms:**
  - "❌ No service found" - Service name doesn't exist or services cache is empty
  - "HTTP 401" - Invalid `RENDER_API_KEY`
  - "HTTP 404" - Service ID or endpoint doesn't exist
  - "HTTP 429" - Rate limiting (rare with Render API)

**What are the recovery procedures?**
1. **Check the Logs:** Look for curl error messages or HTTP status codes in stderr output. The traceback will point to the failing tool.
2. **Verify Environment:** Ensure `RENDER_API_KEY` and `OWNER_ID` are correctly set in the environment (check `.env` file or Claude Code MCP settings).
3. **Test Connection:** Run `render_list_all_services` to verify API connectivity and authentication.
4. **Clear Service Cache:** Restart the server to clear `SERVICES_CACHE` if service names aren't resolving correctly.
5. **Check Render API Status:** Visit Render status page if API calls are timing out or returning 5xx errors.
6. **Validate Service IDs:** Use `render_list_all_services` to get correct service IDs if name resolution fails.

**What scaling concerns exist?**
- **Service Cache:** `SERVICES_CACHE` grows linearly with number of services (currently ~7 services, negligible memory impact).
- **Log Fetching:** The `render_logs` tool fetches up to 100 log entries per call. For high-traffic services, consider reducing limit parameter to avoid timeouts.
- **Curl Subprocess Overhead:** Each API call spawns a subprocess. For bulk operations, consider batching or using aiohttp (like `deploy_tools.py` does).
- **Rate Limiting:** Render API has undocumented rate limits. The server doesn't implement retry logic, so rapid successive calls may fail temporarily.

---

## 6. Available Tools

### Deployment Monitoring
- **`render_deployments`** - Get recent deployment history (status, timestamps, commit info)
- **`render_deploy_details`** - Detailed info about a specific deployment
- **`render_latest_deployment_logs`** - Logs from most recent deployment

### Service Health & Status
- **`render_service_status`** - Current service status, type, plan, URL
- **`render_service_events`** - Intelligent event analysis with actionable recommendations
- **`render_services_status`** - Multi-service overview (summary/detailed/problems modes)

### Logs & Debugging
- **`render_logs`** - Recent service logs with timestamp and level filtering
- **`search_render_logs`** - Search logs for specific text patterns (case-insensitive)
- **`render_recent_errors`** - Filter for ERROR and WARNING level logs only

### Service Management
- **`render_restart_service`** - Restart a running service
- **`render_suspend_service`** - Stop a service (pauses billing)
- **`render_resume_service`** - Resume a suspended service
- **`render_scale_service`** - Scale instances (0 to stop, 1+ to scale up)
- **`render_delete_service`** - Permanently delete a service (irreversible)

### Configuration & Resources
- **`render_environment_vars`** - List env vars (values partially masked)
- **`render_get_custom_domains`** - List custom domains and verification status
- **`render_get_secret_files`** - List secret files configured for service
- **`render_get_service_instances`** - List running instances
- **`render_list_env_groups`** - Shared environment variable groups
- **`render_list_disks`** - Persistent disks for storage
- **`render_list_projects`** - Projects for organizing services
- **`render_list_maintenance_windows`** - Scheduled Render maintenance

### Analytics & Insights
- **`render_list_all_services`** - All services with type, ID, URL, creation date
- **`render_services_cost_analysis`** - Cost breakdown and optimization suggestions
- **`render_services_ssh_info`** - SSH connection details for all services
- **`render_get_user_info`** - Account information

### Deployment Creation (from deploy_tools.py)
- **`create_web_service`** - Create new web service with validation
- **`create_background_worker`** - Create new background worker
- **`trigger_deploy`** - Trigger manual deployment with optional cache clear

---

## 7. Debugging Workflows

### Incident Response (Production Down)
1. **Quick Health Check:** `render_services_status(analysis_level="summary")`
2. **Find Problems:** `render_services_status(analysis_level="problems")`
3. **Check Recent Errors:** `render_recent_errors(limit=50)`
4. **Analyze Events:** `render_service_events()` - Get intelligent analysis with recommendations
5. **Review Deployment:** `render_deployments(limit=5)` - Check if recent deploy failed
6. **Deployment Logs:** `render_latest_deployment_logs(lines=50)` - Investigate build failures

### Debugging Specific Issues
**API Timeouts:**
```
search_render_logs(search_term="timeout", limit=100)
search_render_logs(search_term="OpenWeatherMap", limit=100)
```

**Memory/Performance Issues:**
```
render_service_events()  # Look for unhealthy events
render_get_service_instances()  # Check instance count
```

**Environment Variable Issues:**
```
render_environment_vars()  # Verify config (values masked)
```

### Cost Optimization
1. **Cost Analysis:** `render_services_cost_analysis()`
2. **Find Waste:** `render_services_status(analysis_level="problems")` - Suspended paid services
3. **Cleanup:** `render_delete_service(service_id="srv-xxx")` - Remove unused services

### Deployment Workflow
1. **Validate Locally:** Ensure changes are committed and pushed to GitHub
2. **Create Service:** `create_web_service()` or `create_background_worker()`
3. **Monitor Deployment:** `render_deployments(limit=3)`
4. **Check Logs:** `render_latest_deployment_logs()`
5. **Verify Status:** `render_service_status()`

---

## 8. Design Principles

### LLM-Friendly Output
- All tools return **formatted strings** with semantic prefixes (ERROR:, SUCCESS:, WARNING:) for easy parsing by Claude
- Intelligent summarization instead of raw API responses
- Actionable recommendations embedded in analysis tools
- Consistent timestamp formatting (UTC ISO 8601)

### User Experience
- **Name Resolution:** Users can use service names instead of IDs (`"final-surf-lamp-web"` instead of `"srv-crsfhnqonk40ofe5nvfg"`)
- **Smart Defaults:** If no service ID provided, tools default to first web/background service based on context
- **Progressive Disclosure:** Summary → Detailed → Problems analysis levels for `render_services_status`

### Reliability
- **Input Validation:** Deployment commands checked for common mistakes before service creation
- **Error Sanitization:** User-facing errors are descriptive without exposing sensitive API details
- **Git Workflow Reminders:** Deployment tools remind users to commit and push changes

### Performance
- **Service Caching:** Service name-to-ID mappings cached to avoid repeated API calls
- **Bounded Queries:** Log limits (max 100), deployment limits (max 50) to prevent timeouts
- **Async Architecture:** All API calls use async/await for non-blocking operations
