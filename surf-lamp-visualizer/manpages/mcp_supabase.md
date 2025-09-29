# MCP Supabase

## 1. Overview

**What it does:** This server acts as a secure, read-only gateway that exposes specialized tools for an AI agent (Claude) to query and analyze the production Supabase (PostgreSQL) database.

**Why it exists:** It exists to empower AI-assisted debugging and monitoring. Instead of giving an AI raw, potentially dangerous database credentials, this server provides a safe, curated API. This allows for rapid, complex analysis of production data during incident response without the risk of accidental modification or the slowness of manual queries.

---

## 2. Technical Details

**What would break if this disappeared?**
- The core user-facing application (web app, lamps) would **not** be affected.
- The AI agent's ability to perform deep, real-time analysis of the database would be completely lost.
- Debugging and operational monitoring would revert to being a slow, manual process of writing SQL queries by hand. It is a critical component of the **maintenance and operations** workflow.

**What assumptions does it make?**
- **Environment:** Assumes `DATABASE_URL` is present and correct in its environment to connect to Supabase.
- **Database Schema:** It is **tightly coupled** to the database schema. Queries in tools like `get_user_dashboard_data` assume that tables (`users`, `lamps`) and their columns exist as named. A schema migration could easily break its tools.
- **Network:** Assumes reliable network connectivity to the Supabase endpoint (`aws-0-us-east-1.pooler.supabase.com`).
- **Client:** Assumes it is being called by an MCP-compatible client that understands how to format tool-use requests.

**Where does complexity hide?**
- **Embedded Business Logic:** The real complexity is in the SQL queries inside each tool. `get_lamp_status_summary` contains the specific business logic for what constitutes an "online," "stale," or "offline" lamp (`NOW() - INTERVAL '1 hour'`). This logic must be kept in sync with any similar logic elsewhere in the system.
- **Fuzzy Search:** The `search_users_and_locations` and `get_surf_conditions_by_location` tools use `ILIKE` for fuzzy string matching, which can have performance implications on very large datasets.
- **`execute_safe_query`:** This tool is a potential security risk. While it blocks keywords like `UPDATE` or `DELETE`, a sufficiently creative `SELECT` statement could still cause high database load. Its use should be monitored.

**What stories does the code tell?**
- The very existence of this server tells a story of a system that grew too complex for simple manual debugging.
- The creation of specific tools like `get_user_dashboard_data` and `get_lamp_status_summary` indicates that these were common, repetitive debugging tasks that were automated to save maintainer time.
- The use of `asyncpg` and `FastMCP` shows a need for an efficient, asynchronous server to handle concurrent requests from the AI without blocking.
- The `statement_cache_size=0` setting is a critical lesson learned from working with Supabase's connection pooler (PgBouncer), which requires session-level settings and doesn't play well with prepared statements.

---

## 3. Architecture & Implementation

**How does data flow through this component?**
1. An AI agent (MCP Client) sends a JSON-RPC request to the server, specifying a tool and its parameters.
2. The `FastMCP` server routes the request to the appropriate Python function (e.g., `@mcp.tool() async def get_lamp_status_summary()`).
3. The function establishes a connection to the Supabase database using `asyncpg`.
4. It executes its hardcoded, parameterized SQL query.
5. The database results are serialized into a JSON-friendly format.
6. The formatted JSON is wrapped in a string and sent back to the AI agent as the tool's output.

**Key Functions/Classes:**
- `FastMCP("surf-lamp-supabase")`: The server instance.
- `get_connection()`: Establishes a connection to the database, crucially disabling the statement cache for Supabase compatibility.
- `@mcp.tool()` decorated functions: Each function is a standalone capability exposed to the AI. They are organized by purpose:
    - **Admin/Schema:** `get_database_schema`, `check_database_health`
    - **Read/Query:** `query_table`, `execute_safe_query`
    - **Analytics:** `get_table_stats`
    - **Business-Logic Specific:** `get_user_dashboard_data`, `get_surf_conditions_by_location`, `get_lamp_status_summary`, `search_users_and_locations`
    - **Write/Delete:** `insert_record`, `delete_record` (the most dangerous tools).

**Configuration:**
- The server is configured via a single environment variable: `DATABASE_URL`.
- It runs as a Python application, typically started with `uvicorn` or a similar ASGI server, and communicates over `stdio`.

---

## 4. Integration Points

**What calls this component?**
- An AI agent (Claude) that acts as an MCP client. It is not designed for human or programmatic use otherwise.

**What does this component call?**
- It makes direct SQL queries to the production Supabase PostgreSQL database.

**Data Formats/Contracts:**
- **Ingress:** Standard JSON-RPC 2.0 requests from the MCP client.
- **Egress:** A single JSON string containing the results of the database query. Dates and times are serialized to ISO 8601 format.

---

## 5. Troubleshooting & Failure Modes

**How do you detect issues?**
- **Logs:** The server logs errors to `stderr`. Look for `asyncpg.exceptions` (database errors), connection failures, or tracebacks within a tool's execution.
- **AI Feedback:** The AI agent will report a `ToolExecutionError` if the server crashes, returns malformed data, or a tool throws an unhandled exception.
- **Symptoms:** The AI responds with "I am unable to access the database" or similar messages.

**What are the recovery procedures?**
1. **Check the Logs:** The traceback will almost always point to the failing tool and the specific SQL query that failed.
2. **Verify Environment:** Ensure the `DATABASE_URL` is correctly set in the Render service's environment.
3. **Check for Schema Drift:** If a query is failing, manually run its SQL against the database. It's likely a table or column was renamed or removed. Update the query in the server code to match the new schema.
4. **Test Connection:** Run the `check_database_health` tool to see if the server can connect to the database at all.
5. **Restart the Service:** A simple restart from the Render dashboard can resolve transient connection issues.

**What scaling concerns exist?**
- This is a low-traffic, internal-facing tool. Standard application scaling concerns (load balancing, etc.) do not apply.
- The primary bottleneck is the connection limit on the Supabase database instance. Each tool call opens a new connection. If the AI were to make many concurrent requests, it could exhaust the connection pool. However, this is unlikely with the current single-agent usage pattern.
