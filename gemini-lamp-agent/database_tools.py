#!/usr/bin/env python3
"""
Direct Database Tools for Surf Lamp Agent - FIXED VERSION
Phase 1: Core database operations with SSL support for Render PostgreSQL
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a database connection with proper SSL and timeout handling for Render PostgreSQL"""
    try:
        logger.info("Attempting Render PostgreSQL connection...")
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            sslmode='require',
            connect_timeout=30,
            application_name='surf_lamp_agent'
        )
        
        # Test connection immediately
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
            
        logger.info("Database connection successful!")
        return conn
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e

def get_all_lamp_ids() -> List[int]:
    """Tool 1: Get all active lamp IDs from the database"""
    logger.info("Getting all lamp IDs...")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT lamp_id FROM lamps ORDER BY lamp_id;")
                results = cursor.fetchall()
                lamp_ids = [row['lamp_id'] for row in results]
        
        logger.info(f"Found {len(lamp_ids)} lamps: {lamp_ids}")
        return lamp_ids
        
    except Exception as e:
        logger.error(f"Error getting lamp IDs: {e}")
        return []

def get_lamp_details(lamp_id: int) -> Dict[str, Any]:
    """Tool 2: Get detailed information for a specific lamp"""
    logger.info(f"Getting details for lamp_id: {lamp_id}")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                SELECT 
                    l.arduino_id,
                    l.lamp_id,
                    l.last_updated,
                    du.website_url,
                    ul.api_key,
                    ul.http_endpoint
                FROM lamps l
                LEFT JOIN usage_lamps ul ON l.lamp_id = ul.lamp_id
                LEFT JOIN daily_usage du ON ul.usage_id = du.usage_id
                WHERE l.lamp_id = %s;
                """
                cursor.execute(query, (lamp_id,))
                results = cursor.fetchall()
        
        if not results:
            logger.warning(f"No lamp found with ID: {lamp_id}")
            return {}
            
        # Process results into structured format
        lamp_data = {
            "arduino_id": results[0]["arduino_id"],
            "lamp_id": results[0]["lamp_id"], 
            "last_updated": str(results[0]["last_updated"]) if results[0]["last_updated"] else None,
            "websites": []
        }
        
        # Add website configurations
        for row in results:
            if row["website_url"]:
                lamp_data["websites"].append({
                    "website_url": row["website_url"],
                    "api_key": row["api_key"], 
                    "http_endpoint": row["http_endpoint"]
                })
        
        logger.info(f"Lamp details: arduino_id={lamp_data['arduino_id']}, {len(lamp_data['websites'])} websites")
        return lamp_data
        
    except Exception as e:
        logger.error(f"Error getting lamp details: {e}")
        return {}

def fetch_website_data(api_key: str, endpoint: str) -> Dict[str, Any]:
    """Tool 3: Fetch surf data from website API (MOCK for Phase 1)"""
    logger.info(f"Fetching data from endpoint: {endpoint} (MOCK)")
    
    # Mock data for Phase 1
    mock_data = {
        "status": "mock_success",
        "wave_height_m": 1.5,
        "wave_period_s": 8.0,
        "wind_speed_mps": 12.0,
        "wind_deg": 180,
        "location": "Mock Location",
        "timestamp": int(time.time()),
        "api_endpoint": endpoint,
        "note": "This is mock data - Phase 2 will implement real API calls"
    }
    
    logger.info(f"Mock surf data: {mock_data['wave_height_m']}m waves, {mock_data['wind_speed_mps']}m/s wind")
    return mock_data

def send_to_arduino(arduino_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Tool 4: Send data to Arduino device (MOCK for Phase 1)"""
    logger.info(f"Sending data to Arduino ID: {arduino_id} (MOCK)")
    
    # Mock implementation for Phase 1
    result = {
        "status": "mock_success",
        "arduino_id": arduino_id,
        "message": "Data would be sent via HTTP POST in Phase 2",
        "data_sent": data,
        "timestamp": datetime.now().isoformat(),
        "note": "This is a mock - Phase 2 will implement real HTTP POST to Arduino"
    }
    
    logger.info(f"Mock send to Arduino {arduino_id}: SUCCESS")
    return result

def update_lamp_timestamp(lamp_id: int) -> Dict[str, Any]:
    """Tool 5: Update the last_updated timestamp for a specific lamp"""
    logger.info(f"Updating timestamp for lamp_id: {lamp_id}")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                UPDATE lamps 
                SET last_updated = CURRENT_TIMESTAMP 
                WHERE lamp_id = %s
                RETURNING lamp_id, last_updated;
                """
                cursor.execute(query, (lamp_id,))
                result = cursor.fetchone()
                conn.commit()
        
        if result:
            updated_data = {
                "status": "success",
                "lamp_id": result["lamp_id"],
                "last_updated": str(result["last_updated"]),
                "timestamp": datetime.now().isoformat()
            }
            logger.info(f"Updated lamp {lamp_id} timestamp: {updated_data['last_updated']}")
            return updated_data
        else:
            logger.warning(f"No lamp found with ID: {lamp_id}")
            return {"status": "error", "message": f"Lamp {lamp_id} not found"}
            
    except Exception as e:
        logger.error(f"Error updating lamp timestamp: {e}")
        return {"status": "error", "message": str(e)}

def test_database_connection() -> bool:
    """Test if we can connect to the database"""
    logger.info("Testing database connection...")
    
    # Check environment variables
    env_vars = {
        'DB_HOST': os.getenv('DB_HOST'),
        'DB_PORT': os.getenv('DB_PORT'),
        'DB_NAME': os.getenv('DB_NAME'),
        'DB_USER': os.getenv('DB_USER'),
        'DB_PASSWORD': '***' if os.getenv('DB_PASSWORD') else None
    }
    
    for key, value in env_vars.items():
        if value:
            logger.info(f"{key}: {value}")
        else:
            logger.error(f"{key}: NOT SET")
    
    missing_vars = [k for k, v in env_vars.items() if not v]
    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        return False
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    logger.info("Database connection test: SUCCESS")
                    return True
                else:
                    logger.error("Database connection test: FAILED - unexpected result")
                    return False
    except Exception as e:
        logger.error(f"Database connection test: FAILED - {e}")
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    if test_database_connection():
        print("✅ Database connection works!")
    else:
        print("❌ Database connection failed!")
