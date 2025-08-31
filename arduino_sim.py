#!/usr/bin/env python3
"""
Arduino Simulator Script
Simulates an Arduino device fetching surf data from the server
"""

import requests
import time
import json
import sys
from datetime import datetime

class ArduinoSimulator:
    def __init__(self, arduino_id, api_server="final-surf-lamp.onrender.com"):
        self.arduino_id = arduino_id
        self.api_server = api_server
        self.fetch_interval = 31 * 60  # 31 minutes in seconds
        self.last_surf_data = {}
        
        print(f"Arduino Simulator Started")
        print(f"Arduino ID: {self.arduino_id}")
        print(f"API Server: {self.api_server}")
        print(f"Fetch Interval: {self.fetch_interval} seconds ({self.fetch_interval/60} minutes)")
        print("-" * 50)
    
    def fetch_surf_data(self):
        """Fetch surf data from server (same as Arduino)"""
        url = f"https://{self.api_server}/api/arduino/{self.arduino_id}/data"
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching surf data from: {url}")
        
        try:
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Received surf data from server")
                return data
            else:
                print(f"HTTP error fetching surf data: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            return None
    
    def process_surf_data(self, json_data):
        """Process surf data (simulate Arduino processing)"""
        if not json_data:
            return False
            
        # Extract values (same keys as Arduino expects)
        wave_height_cm = json_data.get('wave_height_cm', 0)
        wave_period_s = json_data.get('wave_period_s', 0.0)
        wind_speed_mps = json_data.get('wind_speed_mps', 0)
        wind_direction_deg = json_data.get('wind_direction_deg', 0)
        wave_threshold_cm = json_data.get('wave_threshold_cm', 100)
        
        print("Surf Data Received:")
        print(f"   Wave Height: {wave_height_cm} cm")
        print(f"   Wave Period: {wave_period_s:.1f} s")
        print(f"   Wind Speed: {wind_speed_mps} m/s")
        print(f"   Wind Direction: {wind_direction_deg}°")
        print(f"   Wave Threshold: {wave_threshold_cm} cm")
        
        # Simulate LED calculations (same as Arduino)
        self.simulate_led_display(wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg, wave_threshold_cm)
        
        # Store data
        self.last_surf_data = {
            'wave_height_m': wave_height_cm / 100.0,
            'wave_period_s': wave_period_s,
            'wind_speed_mps': wind_speed_mps,
            'wind_direction_deg': wind_direction_deg,
            'last_update': time.time(),
            'data_received': True
        }
        
        return True
    
    def simulate_led_display(self, wave_height_cm, wave_period_s, wind_speed_mps, wind_direction_deg, wave_threshold_cm):
        """Simulate LED display calculations (same as Arduino)"""
        # Constants from Arduino code
        NUM_LEDS_CENTER = 12
        NUM_LEDS_RIGHT = 9
        NUM_LEDS_LEFT = 9
        
        # Calculate LED counts (same formulas as Arduino)
        wind_speed_leds = min(int(wind_speed_mps * 1.3) + 1, NUM_LEDS_CENTER - 1)
        wave_height_leds = min(int(wave_height_cm / 25) + 1, NUM_LEDS_RIGHT)
        wave_period_leds = min(int(wave_period_s), NUM_LEDS_LEFT)
        
        # Wind direction color
        if wind_direction_deg < 45 or wind_direction_deg >= 315:
            wind_color = "Green (North)"
        elif 45 <= wind_direction_deg < 135:
            wind_color = "Yellow (East)"
        elif 135 <= wind_direction_deg < 225:
            wind_color = "Red (South)"
        else:
            wind_color = "Blue (West)"
        
        # Threshold alert
        alert_mode = wave_height_cm >= wave_threshold_cm
        
        print("LED Display Simulation:")
        print(f"   Wind Speed LEDs: {wind_speed_leds}/{NUM_LEDS_CENTER-1} (Wind Direction: {wind_color})")
        print(f"   Wave Height LEDs: {wave_height_leds}/{NUM_LEDS_RIGHT} {'[ALERT MODE - 60% BRIGHTER]' if alert_mode else ''}")
        print(f"   Wave Period LEDs: {wave_period_leds}/{NUM_LEDS_LEFT}")
        print(f"   Alert Status: {'ACTIVE' if alert_mode else 'NORMAL'} (Threshold: {wave_threshold_cm}cm)")
    
    def get_status(self):
        """Get current status (similar to Arduino status endpoint)"""
        return {
            'arduino_id': self.arduino_id,
            'status': 'online',
            'uptime_seconds': int(time.time() - self.start_time),
            'simulator': True,
            'last_surf_data': self.last_surf_data,
            'next_fetch_in': max(0, int(self.next_fetch_time - time.time())) if hasattr(self, 'next_fetch_time') else 0
        }
    
    def run_once(self):
        """Run one fetch cycle"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === FETCH CYCLE ===")
        
        data = self.fetch_surf_data()
        if data:
            success = self.process_surf_data(data)
            if success:
                print("Surf data processing completed successfully")
            else:
                print("Surf data processing failed")
        else:
            print("No surf data received")
        
        print("-" * 50)
        return data is not None
    
    def run_continuous(self):
        """Run continuously (like Arduino)"""
        self.start_time = time.time()
        
        print("Starting continuous mode...")
        print("Press Ctrl+C to stop")
        
        # Run initial fetch
        self.run_once()
        
        try:
            while True:
                self.next_fetch_time = time.time() + self.fetch_interval
                next_time_str = datetime.fromtimestamp(self.next_fetch_time).strftime('%H:%M:%S')
                
                print(f"Waiting {self.fetch_interval/60:.0f} minutes until next fetch (at {next_time_str})")
                
                # Sleep in 60-second intervals to allow for status checks
                for i in range(self.fetch_interval):
                    time.sleep(1)
                    
                    # Show countdown every 5 minutes
                    remaining = self.fetch_interval - i
                    if remaining % 300 == 0 and remaining > 0:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Next fetch in {remaining//60} minutes")
                
                # Fetch data
                self.run_once()
                
        except KeyboardInterrupt:
            print(f"\nSimulator stopped by user")
            print(f"Total uptime: {int(time.time() - self.start_time)} seconds")

def main():
    if len(sys.argv) < 2:
        print("Usage: python arduino_simulator.py <arduino_id> [api_server] [mode]")
        print("Examples:")
        print("  python arduino_simulator.py 2545")
        print("  python arduino_simulator.py 2545 final-surf-lamp.onrender.com")
        print("  python arduino_simulator.py 2545 final-surf-lamp.onrender.com once")
        sys.exit(1)
    
    arduino_id = int(sys.argv[1])
    api_server = sys.argv[2] if len(sys.argv) > 2 else "final-surf-lamp.onrender.com"
    mode = sys.argv[3] if len(sys.argv) > 3 else "continuous"
    
    simulator = ArduinoSimulator(arduino_id, api_server)
    
    if mode == "once":
        simulator.run_once()
    else:
        simulator.run_continuous()

if __name__ == "__main__":
    main()
