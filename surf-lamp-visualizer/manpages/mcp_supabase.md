# MCP Supabase 

## 1. Overview

**What it does:** This server acts as a read-only pipe that allows a maintainer to interact with supabase using natural language.

**Why it exists:** To make debugging and retriving information from the database easier and also for any future llm integration to the project.

---

## 2. Technical Details

**What would break if this disappeared?**
- would be harder to interact with the database

**What assumptions does it make?**
- **Environment:** Assumes `DATABASE_URL` is present and correct in its environment to connect to Supabase.
- **Database Schema:** It is **tightly coupled** to the database schema. Queries in tools like `get_user_dashboard_data` assume that tables (`users`, `lamps`) and their columns exist as named. A schema migration could easily break its tools.
- **Network:** Assumes reliable network connectivity to the Supabase endpoint (`aws-0-us-east-1.pooler.supabase.com`).
- **Client:** Assumes it is being called by an MCP-compatible client that understands how to format tool-use requests.

**Where does complexity hide?**
- **Centralized Configuration:** Business logic thresholds now live in `shared_config.py` (LAMP_ONLINE_THRESHOLD_SECONDS, LAMP_STALE_THRESHOLD_SECONDS). The `get_lamp_status_summary` tool dynamically references these values via `get_online_interval_sql()` and `get_stale_interval_sql()`. This ensures synchronization with the monitor and processor components.
- **SQL Injection Protection:** The `validate_where_clause()` function uses regex patterns to block dangerous SQL patterns (semicolons, comments, DROP/DELETE/UNION keywords) and always-true conditions (1=1, 2>1). Applied to `query_table()` and `delete_record()`.
- **Connection Safety:** All database functions use the `DatabaseConnection` async context manager, which guarantees connection cleanup even during exceptions. Prevents connection pool exhaustion.
- **Error Sanitization:** User-facing errors are generic ("Database query failed. Check server logs.") while detailed errors go to `logger.error()` for admin access only. Prevents schema information leakage.
- **Fuzzy Search:** The `search_users_and_locations` and `get_surf_conditions_by_location` tools use `ILIKE` for fuzzy string matching. Performance impact negligible at current scale (7 lamps, <10 users).

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
- `DatabaseConnection`: Async context manager that guarantees connection cleanup. All tools use `async with DatabaseConnection() as conn:` pattern.
- `get_connection()`: Legacy connection method, deprecated in favor of context manager.
- `validate_where_clause()`: SQL injection protection using regex pattern matching.
- `shared_config.py`: Centralized business logic constants (timing thresholds, intervals).
- `@mcp.tool()` decorated functions: Each function is a standalone capability exposed to the AI. They are organized by purpose:
    - **Admin/Schema:** `get_database_schema`, `check_database_health`
    - **Read/Query:** `query_table` (injection-protected), `execute_safe_query`
    - **Analytics:** `get_table_stats`
    - **Business-Logic Specific:** `get_user_dashboard_data`, `get_surf_conditions_by_location`, `get_lamp_status_summary` (uses centralized config), `search_users_and_locations`
    - **Write/Delete:** `insert_record`, `delete_record` (injection-protected, most dangerous tools).

**Configuration:**
- The server is configured via a single environment variable: `DATABASE_URL`.

---

## 4. Integration Points

**What calls this component?**
- Any AI agent that acts as an MCP client.

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
- None

