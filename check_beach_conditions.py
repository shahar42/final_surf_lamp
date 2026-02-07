#!/usr/bin/env python3
"""
Check Surf Conditions for Israeli Beaches
Fetches real-time data from Open-Meteo for all beaches listed in israel_beaches.md.
"""

import os
import sys
import re
import json
import logging
from datetime import datetime

# Add processor to path to use existing logic
processor_path = os.path.join(os.getcwd(), 'surf-lamp-processor')
sys.path.append(processor_path)

try:
    from weather_api_client import fetch_surf_data
    # Suppress logging to keep output clean
    logging.getLogger('weather_api_client').setLevel(logging.ERROR)
    logging.getLogger('surf_data_transformer').setLevel(logging.ERROR)
except ImportError:
    print("❌ Error: Could not import weather_api_client from surf-lamp-processor.")
    sys.exit(1)

def parse_beaches_md(file_path):
    beaches = []
    if not os.path.exists(file_path):
        return beaches

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the table rows (skip header and separator)
    table_started = False
    for line in lines:
        if '|' in line and '---' not in line and 'English Name' not in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                beaches.append({
                    'name': parts[1],
                    'hebrew': parts[2],
                    'lat': parts[3],
                    'lon': parts[4]
                })
    return beaches

def get_conditions(beach):
    lat = beach['lat']
    lon = beach['lon']
    
    # Construct URLs (same as used in the system)
    wave_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height,wave_period,wave_direction"
    wind_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms"
    
    # In the real system, these are fetched and merged
    # Here we do it sequentially
    
    # Note: fetch_surf_data has a 30s sleep. For this script, we might want to bypass it
    # But to stay true to the system's "endpoints", we'll use it but maybe mock the sleep
    # Or just wait if we have few beaches. Let's try with a smaller sample first or bypass sleep.
    
    import requests
    from surf_data_transformer import standardize_surf_data
    
    results = {}
    
    try:
        # Fetch Wave
        resp = requests.get(wave_url, timeout=10)
        if resp.status_code == 200:
            wave_data = standardize_surf_data(resp.json(), wave_url)
            if wave_data:
                results.update(wave_data)
        
        # Fetch Wind
        resp = requests.get(wind_url, timeout=10)
        if resp.status_code == 200:
            wind_data = standardize_surf_data(resp.json(), wind_url)
            if wind_data:
                # Merge wind data into results
                for k, v in wind_data.items():
                    if k not in results or k == 'timestamp':
                        results[k] = v
    except Exception as e:
        print(f"Error fetching for {beach['name']}: {e}")
        
    return results

def main():
    beach_file = 'new_locations/israel_beaches.md'
    beaches = parse_beaches_md(beach_file)
    
    if not beaches:
        print(f"No beaches found in {beach_file}")
        return

    print(f"Checking conditions for {len(beaches)} beaches...\n")
    print(f"{'Beach Name':<25} | {'Wave (m)':<8} | {'Period (s)':<10} | {'Wind (m/s)':<10} | {'Dir':<4}")
    print("-" * 70)

    # To avoid 30s sleep per call in fetch_surf_data, we'll process a few
    # or just use our local fetching logic which is essentially the same
    
    for beach in beaches:
        data = get_conditions(beach)
        
        wave_h = f"{data.get('wave_height_m', 0.0):.2f}" if data.get('wave_height_m') is not None else "N/A"
        wave_p = f"{data.get('wave_period_s', 0.0):.1f}" if data.get('wave_period_s') is not None else "N/A"
        wind_s = f"{data.get('wind_speed_mps', 0.0):.1f}" if data.get('wind_speed_mps') is not None else "N/A"
        wind_d = data.get('wind_direction_deg', "N/A")
        
        print(f"{beach['name']:<25} | {wave_h:<8} | {wave_p:<10} | {wind_s:<10} | {wind_d}")

if __name__ == "__main__":
    main()
