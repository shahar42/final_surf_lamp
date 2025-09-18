#!/usr/bin/env python3
"""
Surf Lamp Supabase MCP Server using FastMCP
Provides access to surf lamp database with proper Claude Code integration.
"""

import os
import sys
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

# MCP imports
from mcp.server.fastmcp import FastMCP

# Database imports
import asyncpg

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

async def get_connection():
    """Get database connection with Supabase-compatible settings"""
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

@mcp.tool()
async def get_database_schema() -> str:
    """ADMIN: Get complete surf lamp database schema showing all table structures, column types, and relationships. Use this to understand the database structure before making complex queries."""
    try:
        conn = await get_connection()

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

        await conn.close()

        return f"Database Schema:\n\n```json\n{json.dumps(schema_info, indent=2, default=str)}\n```"

    except Exception as e:
        logger.error(f"Schema query failed: {e}")
        return f"Error getting database schema: {str(e)}"

@mcp.tool()
async def query_table(table_name: str, limit: int = 10, where_clause: str = "") -> str:
    """READ: Query specific surf lamp tables with optional WHERE filtering. Available tables: users(user_id,username,email,location,theme,wave_threshold_m,wind_threshold_knots), lamps(lamp_id,user_id,arduino_id,arduino_ip), current_conditions(lamp_id,wave_height_m,wave_period_s,wind_speed_mps,wind_direction_deg), daily_usage(usage_id,website_url), usage_lamps(usage_id,lamp_id,api_key,http_endpoint), location_websites(location,usage_id), password_reset_tokens(id,user_id,token_hash,expiration_time). Use for basic table queries with simple filtering."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        if not 1 <= limit <= 100:
            return "Error: limit must be between 1 and 100"

        conn = await get_connection()

        # Build safe query
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" LIMIT {limit}"

        rows = await conn.fetch(query)
        data = [dict(row) for row in rows]

        await conn.close()

        return f"Table '{table_name}' Query Results ({len(data)} rows):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Table query failed: {e}")
        return f"Error querying table {table_name}: {str(e)}"

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
        conn = await get_connection()

        # Add LIMIT if not present
        if 'LIMIT' not in query_upper:
            query += f" LIMIT {limit}"

        rows = await conn.fetch(query)
        data = [dict(row) for row in rows]

        await conn.close()

        return f"Query Results ({len(data)} rows):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return f"Error executing query: {str(e)}"

@mcp.tool()
async def get_table_stats(table_name: str) -> str:
    """ANALYTICS: Get table statistics including row count and column information. Use to understand table size and structure before querying."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        conn = await get_connection()

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

        await conn.close()

        return f"Table '{table_name}' Statistics:\n\n```json\n{json.dumps(stats, indent=2, default=str)}\n```"

    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        return f"Error getting table stats: {str(e)}"

@mcp.tool()
async def check_database_health() -> str:
    """ADMIN: Check Supabase database connection status and get table row counts. Use to verify system health and get quick overview of data volume."""
    try:
        conn = await get_connection()

        # Test connection
        result = await conn.fetchval("SELECT 1")

        # Get table counts
        table_counts = {}
        for table in KNOWN_TABLES:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = count
            except Exception as e:
                table_counts[table] = f"Error: {e}"

        await conn.close()

        health_info = {
            "status": "healthy",
            "connection_test": result,
            "table_counts": table_counts,
            "timestamp": datetime.now().isoformat()
        }

        return f"Database Health Check:\n\n```json\n{json.dumps(health_info, indent=2)}\n```"

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return f"Database health check failed: {str(e)}"

@mcp.tool()
async def get_user_dashboard_data(user_id: int) -> str:
    """SURF: Get complete user dashboard in one call - user profile, all their lamps, and current surf conditions. Perfect for loading user-specific surf lamp data. Returns joined data from users+lamps+current_conditions tables."""
    try:
        if user_id < 1:
            return "Error: user_id must be a positive integer"

        conn = await get_connection()

        # Get user profile, lamps, and current conditions in one go
        query = """
        SELECT
            u.user_id, u.username, u.email, u.location, u.theme, u.preferred_output,
            u.wave_threshold_m, u.wind_threshold_knots,
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

        await conn.close()

        return f"User Dashboard Data (user_id: {user_id}):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Dashboard query failed: {e}")
        return f"Error getting dashboard data for user {user_id}: {str(e)}"

@mcp.tool()
async def get_surf_conditions_by_location(location: str) -> str:
    """SURF: Get current surf conditions for all users/lamps in a specific location. Perfect for location-based surf reports showing wave height, period, wind speed/direction. Uses fuzzy location matching (partial strings work)."""
    try:
        if len(location) < 2:
            return "Error: location must be at least 2 characters"

        conn = await get_connection()

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

        await conn.close()

        return f"Surf Conditions for '{location}' ({len(data)} results):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Location conditions query failed: {e}")
        return f"Error getting conditions for location '{location}': {str(e)}"

@mcp.tool()
async def get_lamp_status_summary() -> str:
    """MONITORING: Get operational status of all surf lamps with real-time health indicators. Shows online/stale/offline status based on last data update, Arduino connectivity, and user ownership. Perfect for system monitoring."""
    try:
        conn = await get_connection()

        query = """
        SELECT
            l.lamp_id, l.user_id, u.username, l.arduino_id, l.arduino_ip,
            l.last_updated as lamp_updated,
            cc.last_updated as conditions_updated,
            CASE
                WHEN cc.last_updated > NOW() - INTERVAL '1 hour' THEN 'online'
                WHEN cc.last_updated > NOW() - INTERVAL '24 hours' THEN 'stale'
                ELSE 'offline'
            END as status
        FROM lamps l
        JOIN users u ON l.user_id = u.user_id
        LEFT JOIN current_conditions cc ON l.lamp_id = cc.lamp_id
        ORDER BY l.lamp_id
        """
        rows = await conn.fetch(query)
        data = [dict(row) for row in rows]

        await conn.close()

        return f"Lamp Status Summary ({len(data)} lamps):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Lamp status query failed: {e}")
        return f"Error getting lamp status: {str(e)}"

@mcp.tool()
async def search_users_and_locations(search_term: str) -> str:
    """SEARCH: Find users by partial username, email, or location using fuzzy search. Perfect for user discovery and location-based queries. Searches across all user text fields simultaneously."""
    try:
        if len(search_term) < 2:
            return "Error: search_term must be at least 2 characters"

        conn = await get_connection()

        query = """
        SELECT user_id, username, email, location, theme
        FROM users
        WHERE username ILIKE $1 OR email ILIKE $1 OR location ILIKE $1
        ORDER BY username
        """
        rows = await conn.fetch(query, f"%{search_term}%")
        data = [dict(row) for row in rows]

        await conn.close()

        return f"Search Results for '{search_term}' ({len(data)} matches):\n\n```json\n{json.dumps(data, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Search query failed: {e}")
        return f"Error searching for '{search_term}': {str(e)}"

@mcp.tool()
async def insert_record(table_name: str, data: Dict[str, Any]) -> str:
    """WRITE: Insert a new record into any surf lamp table. Automatically handles ID generation for tables with auto-increment primary keys. Use for adding new users, lamps, conditions, etc."""
    try:
        if table_name not in KNOWN_TABLES:
            return f"Error: table_name must be one of {KNOWN_TABLES}"

        if not data:
            return "Error: data cannot be empty"

        conn = await get_connection()

        # Build INSERT query
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())

        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING *"

        # Execute insert and return the new record
        result = await conn.fetchrow(query, *values)
        new_record = dict(result) if result else {}

        await conn.close()

        return f"Successfully inserted into '{table_name}':\n\n```json\n{json.dumps(new_record, indent=2, default=serialize_for_json)}\n```"

    except Exception as e:
        logger.error(f"Insert failed: {e}")
        return f"Error inserting into {table_name}: {str(e)}"

# Test database connection on startup
async def test_connection():
    """Test database connection on startup"""
    try:
        conn = await get_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
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
    mcp.run(host='0.0.0.0', port=8080)