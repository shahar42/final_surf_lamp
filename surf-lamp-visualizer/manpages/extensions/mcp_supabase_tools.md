# Supabase MCP Server Tools

Complete reference for all Supabase database tools.

---

## get_database_schema
Shows all database table structures, columns, types, and relationships.

## query_table
Queries specific table with optional WHERE filter and limit.

## execute_safe_query
Runs complex custom SELECT queries with joins and aggregations.

## get_table_stats
Shows row counts and column information for specific table.

## check_database_health
Verifies database connection is healthy and returns table counts.

## get_user_dashboard_data
Fetches all user data including lamps and surf conditions.

## get_surf_conditions_by_location
Gets current surf conditions for all users in location.

## get_lamp_status_summary
Summarizes operational status of all lamps with health indicators.

## search_users_and_locations
Finds users by partial username, email, or location match.

## insert_record
Adds new record to any table with automatic ID generation.

## delete_record
Deletes records from table using WHERE clause. Caution: permanent deletion.