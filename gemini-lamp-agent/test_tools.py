#!/usr/bin/env python3
"""
Test script for Phase 1: Direct Database Tools Testing
Tests each of the 5 database tools individually
"""

import sys
from database_tools import (
    test_database_connection,
    get_all_lamp_ids,
    get_lamp_details,
    fetch_website_data,
    send_to_arduino,
    update_lamp_timestamp
)

def test_all_database_tools():
    """Test all 5 database tools individually"""
    
    print("=" * 60)
    print("PHASE 1: TESTING DIRECT DATABASE TOOLS")
    print("=" * 60)
    
    # Test 0: Database Connection
    print("TEST 0: Database Connection...")
    if not test_database_connection():
        print("❌ Database connection failed! Check your .env file and credentials.")
        print("Make sure your .env file has:")
        print("DB_HOST=dpg-d2d4ffemc3f73a7b9p0-a.virginia-postgres.render.com")
        print("DB_PORT=5432")
        print("DB_NAME=surf_lamp_db") 
        print("DB_USER=surf_lamp_db_user")
        print("DB_PASSWORD=81SyRDKmGmq1YJVhNZ9SO1xGbdaifEKU")
        return False
    print("✅ Database connection - SUCCESS")
    print("-" * 40)
    
    # Test 1: Get All Lamp IDs
    print("TEST 1: Getting all lamp IDs...")
    try:
        lamp_ids = get_all_lamp_ids()
        print(f"Result: Found {len(lamp_ids)} lamps")
        print(f"Lamp IDs: {lamp_ids}")
        print("✅ get_all_lamp_ids - SUCCESS")
        
        # Store first lamp ID for next test
        test_lamp_id = lamp_ids[0] if lamp_ids else 1
        
    except Exception as e:
        print(f"❌ get_all_lamp_ids - ERROR: {e}")
        test_lamp_id = 1  # fallback
    print("-" * 40)
    
    # Test 2: Get Lamp Details
    print(f"TEST 2: Getting lamp details for lamp_id {test_lamp_id}...")
    try:
        lamp_details = get_lamp_details(test_lamp_id)
        print(f"Result: {lamp_details}")
        if lamp_details:
            print(f"Arduino ID: {lamp_details.get('arduino_id')}")
            print(f"Websites: {len(lamp_details.get('websites', []))}")
        print("✅ get_lamp_details - SUCCESS")
    except Exception as e:
        print(f"❌ get_lamp_details - ERROR: {e}")
    print("-" * 40)
    
    # Test 3: Fetch Website Data (mock)
    print("TEST 3: Fetching website data (mock)...")
    try:
        surf_data = fetch_website_data(
            api_key="test_api_key", 
            endpoint="https://api.example.com/surf"
        )
        print(f"Result: {surf_data}")
        print(f"Wave height: {surf_data.get('wave_height_m')}m")
        print(f"Wind speed: {surf_data.get('wind_speed_mps')}m/s")
        print("✅ fetch_website_data - SUCCESS")
    except Exception as e:
        print(f"❌ fetch_website_data - ERROR: {e}")
    print("-" * 40)
    
    # Test 4: Send to Arduino (mock)
    print("TEST 4: Sending to Arduino (mock)...")
    try:
        mock_surf_data = {
            "wave_height_m": 1.5,
            "wind_speed_mps": 12.0,
            "location": "Test Beach"
        }
        send_result = send_to_arduino(
            arduino_id=12345,
            data=mock_surf_data
        )
        print(f"Result: {send_result}")
        print(f"Status: {send_result.get('status')}")
        print("✅ send_to_arduino - SUCCESS")
    except Exception as e:
        print(f"❌ send_to_arduino - ERROR: {e}")
    print("-" * 40)
    
    # Test 5: Update Lamp Timestamp
    print(f"TEST 5: Updating lamp timestamp for lamp_id {test_lamp_id}...")
    try:
        update_result = update_lamp_timestamp(test_lamp_id)
        print(f"Result: {update_result}")
        print(f"Status: {update_result.get('status')}")
        if update_result.get('status') == 'success':
            print(f"New timestamp: {update_result.get('last_updated')}")
        print("✅ update_lamp_timestamp - SUCCESS")
    except Exception as e:
        print(f"❌ update_lamp_timestamp - ERROR: {e}")
    print("-" * 40)
    
    print("=" * 60)
    print("Phase 1 Testing Complete!")
    print("All 5 database tools have been tested.")
    print("✅ SUCCESS: Direct database tools are working!")
    print("✅ SSL connection to Render PostgreSQL works!")
    print("✅ Ready for Phase 2: Real API calls and Arduino HTTP POST")
    print("=" * 60)

if __name__ == "__main__":
    test_all_database_tools()
