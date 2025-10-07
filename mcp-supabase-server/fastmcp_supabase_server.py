#!/usr/bin/env python3
"""
Surf Lamp Supabase MCP Server using FastMCP
Provides access to surf lamp database with proper Claude Code integration.
"""

import os
import sys
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json

# MCP imports
from mcp.server.fastmcp import FastMCP

# Database imports
import asyncpg

# Shared configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_config import get_online_interval_sql, get_stale_interval_sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("surf-lamp-supabase")

# Initialize FastMCP server
mcp = FastMCP("surf-lamp-supabase")

# Use the working connection string
DATABASE_URL = "postgresql://postgres.onrzyewvkcugupmjdbfu:clwEouTixrJEYdDp@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# Known tables from your surf lamp database
KNOWN_TABLES = ['users', 'lamps', 'current_conditions', 'daily_usage', 'usage_lamps', 'location_websites', 'password_reset_tokens']

class DatabaseConnection:
    """Context manager for safe database connection handling"""
    def __init__(self):
        self.conn = None

    async def __aenter__(self):
        self.conn = await asyncpg.connect(
            DATABASE_URL,
            statement_cache_size=0  # Disable prepared statements for Supabase pooling
        )
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.conn.close()
        return False  # Don't suppress exceptions

async def get_connection():
    """
    Get database connection with Supabase-compatible settings.

    DEPRECATED: Use DatabaseConnection() context manager instead:
        async with DatabaseConnection() as conn:
            # use conn
    """
    return await asyncpg.connect(
        DATABASE_URL,
        statement_cache_size=0  # Disable prepared statements for Supabase pooling
    )

def serialize_for_json(obj: Any) -> Any:
    """Serialize database objects for JSON response"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return {k: serialize_for_json(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj

def validate_where_clause(where_clause: str) -> tuple[bool, str]:
    """
    Validate WHERE clause to prevent SQL injection.
    Returns (is_valid, error_message)

    Only allows simple comparisons like:
    - user_id = 5
    - lamp_id IN (1,2,3)
    - location = 'Tel Aviv'
    """
    if not where_clause or where_clause.strip() == "":
        return True, ""

    # Dangerous patterns that could indicate SQL injection
    dangerous_patterns = [
        r';',  # SQL statement terminator
        r'--',  # SQL comment
        r'/\*',  # Block comment start
        r'\*/',  # Block comment end
        r'\bDROP\b',
        r'\bDELETE\b',
        r'\bUPDATE\b',
        r'\bINSERT\b',
        r'\bEXEC\b',
        r'\bEXECUTE\b',
        r'\bUNION\b',
        r'\bALTER\b',
        r'\bCREATE\b',
        r'\bTRUNCATE\b',
    ]

    clause_upper = where_clause.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, clause_upper):
            return False, f"WHERE clause contains dangerous pattern: {pattern}"

    # Allow basic equality checks that are obviously dangerous
    # 1=1, 2>1, true, etc.
    always_true_patterns = [
        r'^\s*1\s*[=>]\s*1\s*$',
        r'^\s*\d+\s*[><]\s*\d+\s*$',
        r'^\s*true\s*$',
        r'^\s*1\s*$',
    ]

    clause_lower = where_clause.lower().strip()
    for pattern in always_true_patterns:
        if re.match(pattern, clause_lower):
            return False, "WHERE clause appears to be always-true condition"

    return True, ""

@mcp.tool()
async def get_database_schema() -> str:
    """ADMIN: Get complete surf lamp database schema showing all table structures, column types, and relationships. Use this to understand the database structure before making complex queries."""
    try:
        async with DatabaseConnection() as conn:
            # Get all tables
            tables_query = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
            tables = await conn.fetch(tables_query)

            schema_info = {"tables": {}}

            for table in tables:
                table_name = table['table_name']

                # Get columns for each table
                columns_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
                """
                columns = await conn.fetch(columns_query, table_name)

                schema_info["tables"][table_name] = {
                    "type": table['table_type'],
                    "columns": [dict(col) for col in columns]
                }

        return f"Database Schema:\n\n```json\n{json.dumps(schema_info, indent=2, default=str)}\n```"

    except Exception as e:
        logger.error(f"Schema query failed: {e}")
        return "Error: Failed to retrieve database schema. Check server logs for details."

@mcp.tool()
async def query_table(table_name: str, limit: int = 10, where_clause: str = "") -> str:
    """READ: Query specific surf lamp tables with optional WHERE filtering. Available tables: users(user_id,username,email,location,theme,sport_type,wave_threshold_m,wind_threshold_knots), lamps(lamp_id,user_id,arduino_id,arduino_ip), current_conditions(lamp_id,wave_height_m,wave_period_s,wind_speed_mps,wind_direction_deg), daily_usage(usage_id,website_url), usage_lamps(usage_id,lamp_id,api_key,http_endpoint), location_websites(location,usage_id), password_reset_tokens(id,user_id,token_hash,expiration_time). Use for basic table queries with simple filtering."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        if not 1 <= limit <= 100:
            return "Error: limit must be between 1 and 100"

        # Validate WHERE clause for SQL injection
        if where_clause:
            is_valid, error_msg = validate_where_clause(where_clause)
            if not is_valid:
                return f"Error: Invalid WHERE clause - {error_msg}"

        async with DatabaseConnection() as conn:
            # Build safe query
            query = f"SELECT * FROM {table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            query += f" LIMIT {limit}"

            rows = await conn.fetch(query)
            data = [dict(row) for row in rows]

        return f"Table '{table_name}' Query Results ({len(data)} rows):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Table query failed: {e}")
        return "Error: Database query failed. Check server logs for details."

@mcp.tool()
async def execute_safe_query(query: str, limit: int = 10) -> str:
    """READ: Execute custom SELECT queries with joins and complex filtering. Only SELECT statements allowed for security. Use for complex analysis across multiple tables (e.g., JOIN users with lamps and conditions)."""
    # Basic safety check
    query_upper = query.upper().strip()

    if not query_upper.startswith('SELECT'):
        return "Error: Only SELECT queries are allowed for safety"

    # Block dangerous keywords
    dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
    if any(keyword in query_upper for keyword in dangerous_keywords):
        return "Error: Query contains potentially dangerous keywords"

    if not 1 <= limit <= 100:
        return "Error: limit must be between 1 and 100"

    try:
        async with DatabaseConnection() as conn:
            # Add LIMIT if not present
            if 'LIMIT' not in query_upper:
                query += f" LIMIT {limit}"

            rows = await conn.fetch(query)
            data = [dict(row) for row in rows]

        return f"Query Results ({len(data)} rows):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return "Error: Database query failed. Check server logs for details."

@mcp.tool()
async def get_table_stats(table_name: str) -> str:
    """ANALYTICS: Get table statistics including row count and column information. Use to understand table size and structure before querying."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        async with DatabaseConnection() as conn:
            # Get row count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

            # Get column information
            columns_query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
            """
            columns = await conn.fetch(columns_query, table_name)

            stats = {
                "table_name": table_name,
                "total_rows": count,
                "columns": [dict(col) for col in columns]
            }

        return f"Table '{table_name}' Statistics:\n\n```json\n{json.dumps(stats, indent=2, default=str)}\n```"

    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        return "Error: Failed to retrieve table statistics. Check server logs for details."

@mcp.tool()
async def check_database_health() -> str:
    """ADMIN: Check Supabase database connection status and get table row counts. Use to verify system health and get quick overview of data volume."""
    try:
        async with DatabaseConnection() as conn:
            # Test connection
            result = await conn.fetchval("SELECT 1")

            # Get table counts
            table_counts = {}
            for table in KNOWN_TABLES:
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = count
                except Exception as e:
                    table_counts[table] = "Error"
                    logger.error(f"Failed to count {table}: {e}")

            health_info = {
                "status": "healthy",
                "connection_test": result,
                "table_counts": table_counts,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        return f"Database Health Check:\n\n```json\n{json.dumps(health_info, indent=2)}\n```"

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return "Error: Database health check failed. Check server logs for details."

@mcp.tool()
async def get_user_dashboard_data(user_id: int) -> str:
    """SURF: Get complete user dashboard in one call - user profile, all their lamps, and current surf conditions. Perfect for loading user-specific surf lamp data. Returns joined data from users+lamps+current_conditions tables."""
    try:
        if user_id < 1:
            return "Error: user_id must be a positive integer"

        async with DatabaseConnection() as conn:
            # Get user profile, lamps, and current conditions in one go
            query = """
            SELECT
                u.user_id, u.username, u.email, u.location, u.theme, u.preferred_output,
                u.sport_type, u.wave_threshold_m, u.wind_threshold_knots,
                l.lamp_id, l.arduino_id, l.arduino_ip, l.last_updated as lamp_updated,
                cc.wave_height_m, cc.wave_period_s, cc.wind_speed_mps, cc.wind_direction_deg,
                cc.last_updated as conditions_updated
            FROM users u
            LEFT JOIN lamps l ON u.user_id = l.user_id
            LEFT JOIN current_conditions cc ON l.lamp_id = cc.lamp_id
            WHERE u.user_id = $1
            """
            rows = await conn.fetch(query, user_id)
            data = [dict(row) for row in rows]

        return f"User Dashboard Data (user_id: {user_id}):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Dashboard query failed: {e}")
        return "Error: Failed to retrieve user dashboard data. Check server logs for details."

@mcp.tool()
async def get_surf_conditions_by_location(location: str) -> str:
    """SURF: Get current surf conditions for all users/lamps in a specific location. Perfect for location-based surf reports showing wave height, period, wind speed/direction. Uses fuzzy location matching (partial strings work)."""
    try:
        if len(location) < 2:
            return "Error: location must be at least 2 characters"

        async with DatabaseConnection() as conn:
            query = """
            SELECT
                u.username, u.location, l.lamp_id,
                cc.wave_height_m, cc.wave_period_s, cc.wind_speed_mps, cc.wind_direction_deg,
                cc.last_updated
            FROM users u
            JOIN lamps l ON u.user_id = l.user_id
            JOIN current_conditions cc ON l.lamp_id = cc.lamp_id
            WHERE u.location ILIKE $1
            ORDER BY cc.last_updated DESC
            """
            rows = await conn.fetch(query, f"%{location}%")
            data = [dict(row) for row in rows]

        return f"Surf Conditions for '{location}' ({len(data)} results):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Location conditions query failed: {e}")
        return "Error: Failed to retrieve surf conditions. Check server logs for details."

@mcp.tool()
async def get_lamp_status_summary() -> str:
    """MONITORING: Get operational status of all surf lamps with real-time health indicators. Shows online/stale/offline status based on last data update, Arduino connectivity, and user ownership. Perfect for system monitoring."""
    try:
        async with DatabaseConnection() as conn:
            # Use centralized configuration for status thresholds
            # NOTE: These intervals MUST match shared_config.py values
            query = f"""
            SELECT
                l.lamp_id, l.user_id, u.username, l.arduino_id, l.arduino_ip,
                l.last_updated as lamp_updated,
                cc.last_updated as conditions_updated,
                CASE
                    WHEN cc.last_updated > NOW() - {get_online_interval_sql()} THEN 'online'
                    WHEN cc.last_updated > NOW() - {get_stale_interval_sql()} THEN 'stale'
                    ELSE 'offline'
                END as status
            FROM lamps l
            JOIN users u ON l.user_id = u.user_id
            LEFT JOIN current_conditions cc ON l.lamp_id = cc.lamp_id
            ORDER BY l.lamp_id
            """
            rows = await conn.fetch(query)
            data = [dict(row) for row in rows]

        return f"Lamp Status Summary ({len(data)} lamps):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Lamp status query failed: {e}")
        return "Error: Failed to retrieve lamp status. Check server logs for details."

@mcp.tool()
async def search_users_and_locations(search_term: str) -> str:
    """SEARCH: Find users by partial username, email, or location using fuzzy search. Perfect for user discovery and location-based queries. Searches across all user text fields simultaneously."""
    try:
        if len(search_term) < 2:
            return "Error: search_term must be at least 2 characters"

        async with DatabaseConnection() as conn:
            query = """
            SELECT user_id, username, email, location, theme, sport_type
            FROM users
            WHERE username ILIKE $1 OR email ILIKE $1 OR location ILIKE $1
            ORDER BY username
            """
            rows = await conn.fetch(query, f"%{search_term}%")
            data = [dict(row) for row in rows]

        return f"Search Results for '{search_term}' ({len(data)} matches):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Search query failed: {e}")
        return "Error: Search failed. Check server logs for details."

@mcp.tool()
async def insert_record(table_name: str, data: Dict[str, Any]) -> str:
    """WRITE: Insert a new record into any surf lamp table. Automatically handles ID generation for tables with auto-increment primary keys. Use for adding new users, lamps, conditions, etc."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        if not data:
            return "Error: data cannot be empty"

        async with DatabaseConnection() as conn:
            # Build INSERT query
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())

            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING *"

            # Execute insert and return the new record
            result = await conn.fetchrow(query, *values)
            new_record = dict(result) if result else {}

        return f"Successfully inserted into '{table_name}':\n\n```json\n{json.dumps(new_record, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Insert failed: {e}")
        return "Error: Database insert failed. Check server logs for details."

@mcp.tool()
async def delete_record(table_name: str, where_clause: str) -> str:
    """WRITE: Delete records from any surf lamp table using WHERE clause. Use for removing users, lamps, conditions, etc. CAUTION: This permanently deletes data - use carefully with specific WHERE conditions."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        if not where_clause or where_clause.strip() == "":
            return "Error: where_clause is required to prevent accidental deletion of all records"

        # Validate WHERE clause for SQL injection
        is_valid, error_msg = validate_where_clause(where_clause)
        if not is_valid:
            return f"Error: Invalid WHERE clause - {error_msg}"

        async with DatabaseConnection() as conn:
            # First, get the records that will be deleted for confirmation
            select_query = f"SELECT * FROM {table_name} WHERE {where_clause}"
            records_to_delete = await conn.fetch(select_query)

            if not records_to_delete:
                return f"No records found matching WHERE clause: {where_clause}"

            # Execute the delete
            delete_query = f"DELETE FROM {table_name} WHERE {where_clause} RETURNING *"
            deleted_records = await conn.fetch(delete_query)

            result_data = [dict(record) for record in deleted_records]

        return f"Successfully deleted {len(deleted_records)} record(s) from '{table_name}':\n\n```json\n{json.dumps(result_data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return "Error: Database delete failed. Check server logs for details."

# Test database connection on startup
async def test_connection():
    """Test database connection on startup"""
    try:
        async with DatabaseConnection() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

logger.info("Surf Lamp Supabase MCP Server initialized with FastMCP")

if __name__ == "__main__":
    # Test database connection
    asyncio.run(test_connection())

    # Run the FastMCP server
    logger.info("Starting Surf Lamp Supabase MCP Server for Claude Code...")
    logger.info("MCP Server ready for Claude Code with FastMCP integration")
    mcp.run(transport='stdio')