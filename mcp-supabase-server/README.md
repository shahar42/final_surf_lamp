# MCP Supabase Server for Surf Lamp Project

This Model Context Protocol (MCP) server provides Claude Code with direct access to your Supabase database for the Surf Lamp project. It enables safe database operations through standardized tools while maintaining security and data integrity.

## Features

### 🔍 **Schema Introspection**
- Complete database schema exploration
- Table structure analysis with columns, types, and constraints
- Relationship mapping between tables

### 📊 **Data Querying**
- Safe SELECT operations with filtering and ordering
- Custom SQL query execution (read-only)
- Built-in query validation and safety checks
- Automatic result limiting to prevent memory issues

### ✏️ **Data Modification**
- Secure INSERT operations for new records
- UPDATE operations for existing records
- Validation against existing table schemas

### 🏥 **Health Monitoring**
- Database connection health checks
- Table statistics and row counts
- Recent activity monitoring

### 🔒 **Security Features**
- Read-only query enforcement for custom SQL
- Table name validation against known schema
- Query result size limits
- Safe serialization of database objects

## Installation

1. **Install Dependencies**
   ```bash
   cd mcp-supabase-server
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. **Test Connection**
   ```bash
   python mcp_server.py
   ```

## Configuration for Claude Code CLI

### Quick Setup for Claude Code CLI

1. **Set your DATABASE_URL environment variable:**
   ```bash
   export DATABASE_URL="postgresql://postgres:your-password@your-host:5432/postgres"
   ```

2. **Test the FastMCP server:**
   ```bash
   cd mcp-supabase-server
   python test_fastmcp_server.py
   ```

3. **Use with Claude Code CLI:**
   The server will be automatically discovered when you run Claude Code in this directory. Claude Code will use the `claude_code_config.json` configuration.

### Manual Configuration (if needed)

Add this MCP server to your Claude Code configuration file:

```json
{
  "mcpServers": {
    "surf-lamp-supabase": {
      "command": "python",
      "args": ["/home/shahar42/Git_Surf_Lamp_Agent/mcp-supabase-server/fastmcp_server.py"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}",
        "PYTHONPATH": "/home/shahar42/Git_Surf_Lamp_Agent"
      }
    }
  }
}
```

### Enhanced Features (FastMCP)

This server now includes:

- **FastMCP Framework**: Modern async development with better performance
- **PostgreSQL Optimizations**: Native asyncpg connection pooling and prepared statements
- **MCP Resources**: Large table data access with pagination
- **MCP Prompts**: Guided database interactions for common tasks
- **Enhanced Logging**: Proper stderr logging for Claude Code debugging

## Available Tools

### Schema Tools

#### `get_database_schema`
Returns the complete database schema including all tables, columns, relationships, and constraints.

**Usage:**
```python
# Claude Code will automatically use this tool when you ask:
# "Show me the database schema"
```

#### `describe_table`
Get detailed information about a specific table.

**Parameters:**
- `table_name`: Name of the table (users, lamps, current_conditions, etc.)

**Usage:**
```python
# Claude Code example:
# "Describe the users table structure"
```

### Data Query Tools

#### `select_from_table`
Select data from a table with optional filtering and ordering.

**Parameters:**
- `table_name`: Table to query
- `columns`: Array of column names (default: all)
- `where_clause`: Optional WHERE condition
- `limit`: Maximum rows to return (default: 100, max: 1000)
- `order_by`: Optional ORDER BY clause

**Usage:**
```python
# Claude Code examples:
# "Show me all users from Tel Aviv"
# "Get the latest 10 surf conditions"
# "List all lamps with their Arduino IDs"
```

#### `execute_safe_query`
Execute custom SQL queries with safety restrictions.

**Parameters:**
- `query`: SQL SELECT statement
- `limit`: Maximum rows to return

**Safety Features:**
- Only SELECT statements allowed
- Blocks dangerous keywords (DROP, DELETE, etc.)
- Automatic LIMIT enforcement

**Usage:**
```python
# Claude Code examples:
# "Run this query: SELECT u.username, l.arduino_id FROM users u JOIN lamps l ON u.user_id = l.user_id"
```

### Data Modification Tools

#### `insert_record`
Insert a new record into a table.

**Parameters:**
- `table_name`: Target table
- `data`: Key-value pairs for the new record

**Usage:**
```python
# Claude Code example:
# "Add a new user with username 'test_user' and email 'test@example.com'"
```

#### `delete_record`
Delete records from a table using a WHERE clause.

**Parameters:**
- `table_name`: Target table
- `where_clause`: SQL WHERE condition to specify which records to delete

**Safety Features:**
- Requires specific WHERE clause (prevents accidental mass deletion)
- Shows records that will be deleted before executing
- Blocks dangerous WHERE clauses like `1=1`
- Returns deleted records for confirmation

**Usage:**
```python
# Claude Code examples:
# "Delete user with ID 123"
# "Remove all lamps that haven't been updated in 30 days"
# "Delete surf conditions older than 1 week"
```

**⚠️ Permission Required:** This tool requires explicit permission before use. Configure in Claude Code settings with:
```json
{
  "permissions": {
    "ask": ["mcp__surf-lamp-supabase__delete_record"]
  }
}
```

### Monitoring Tools

#### `check_database_health`
Verify database connectivity and get basic statistics.

**Usage:**
```python
# Claude Code example:
# "Check if the database is healthy"
```

#### `get_table_stats`
Get statistical information about a table.

**Parameters:**
- `table_name`: Table to analyze

**Usage:**
```python
# Claude Code example:
# "Show me statistics for the current_conditions table"
```

## Database Schema Reference

The MCP server works with these Surf Lamp database tables:

### Core Tables
- **`users`** - User accounts and preferences
- **`lamps`** - Physical Arduino devices
- **`current_conditions`** - Latest surf data for each device
- **`daily_usage`** - API endpoint configurations
- **`usage_lamps`** - Lamp-to-API endpoint mappings
- **`password_reset_tokens`** - Secure password recovery tokens

### Example Queries

```sql
-- Get all users and their lamp counts
SELECT u.username, u.location, COUNT(l.lamp_id) as lamp_count
FROM users u
LEFT JOIN lamps l ON u.user_id = l.user_id
GROUP BY u.user_id, u.username, u.location;

-- Show recent surf conditions
SELECT l.arduino_id, cc.wave_height_m, cc.wind_speed_mps, cc.last_updated
FROM current_conditions cc
JOIN lamps l ON cc.lamp_id = l.lamp_id
ORDER BY cc.last_updated DESC;

-- User preferences analysis
SELECT location, COUNT(*) as user_count,
       AVG(wave_threshold_m) as avg_wave_threshold,
       AVG(wind_threshold_knots) as avg_wind_threshold
FROM users
GROUP BY location;
```

## Security Considerations

### Permission-Based Tool Access
- **Write operations require explicit permission**: `insert_record` and `delete_record` tools require user approval before execution
- Configure in Claude Code settings to prompt for permission:
  ```json
  {
    "permissions": {
      "ask": [
        "mcp__surf-lamp-supabase__insert_record",
        "mcp__surf-lamp-supabase__delete_record"
      ]
    }
  }
  ```

### Read-Only Enforcement
- Custom SQL queries are restricted to SELECT statements only
- Dangerous keywords (DROP, DELETE, UPDATE, INSERT, ALTER) are blocked in custom queries
- Query results are automatically limited to prevent resource exhaustion

### Data Validation
- Table names are validated against the known schema
- DELETE operations require specific WHERE clauses to prevent mass deletion
- Input sanitization prevents SQL injection
- Dangerous WHERE clauses (like `1=1`) are blocked

### Connection Security
- Uses existing Supabase connection with SSL
- Inherits authentication from your DATABASE_URL
- No hardcoded credentials in the code

## Troubleshooting

### Connection Issues
1. Verify your DATABASE_URL is correctly set
2. Test connection using the parent project's test scripts
3. Check Supabase dashboard for network restrictions

### Permission Errors
1. Ensure your Supabase user has appropriate table permissions
2. Verify the database schema matches the expected tables
3. Check that all required environment variables are set

### Query Errors
1. Use `describe_table` to verify column names and types
2. Check that WHERE clauses use valid column names
3. Ensure data types match when inserting/updating

## Integration Examples

### Daily Usage Analysis
```python
# Claude Code can analyze API usage patterns:
# "Show me the API endpoint usage statistics by location"
# "Which APIs are failing most often?"
# "What's the average response time by endpoint?"
```

### User Behavior Analysis
```python
# Analyze user preferences:
# "What are the most popular surf locations?"
# "Show me users with custom thresholds vs. defaults"
# "Which users haven't updated their lamps recently?"
```

### System Health Monitoring
```python
# Monitor system health:
# "Check if all lamps have recent surf data"
# "Show me any Arduino devices that haven't connected recently"
# "Are there any database tables with unusual activity?"
```

## Contributing

This MCP server is designed to work specifically with the Surf Lamp project's database schema. When adding new tables or columns to the main project:

1. Update the `TABLE_MODELS` dictionary in `mcp_server.py`
2. Import new SQLAlchemy models from the parent project
3. Test all operations with the new schema
4. Update this documentation

## Support

For issues specific to this MCP server, check:
1. Database connectivity using the parent project's tools
2. MCP protocol compatibility with Claude Code
3. Python environment and dependency versions

For Surf Lamp project issues, refer to the main project documentation.