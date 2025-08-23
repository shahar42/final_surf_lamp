#!/usr/bin/env python3
# set_arduino_ip.py
"""
Interactive script to update an Arduino's IP address in the database.

Prompts the user for an Arduino ID and the IP address, then performs
the necessary database update.
"""

import os
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- Functions ---

def get_db_engine():
    """Creates and returns a SQLAlchemy database engine."""
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("   Please ensure your .env file is configured correctly.")
        return None
    try:
        engine = create_engine(DATABASE_URL)
        return engine
    except Exception as e:
        print(f"❌ ERROR: Failed to create database engine: {e}")
        return None

def is_valid_ip(ip):
    """Basic validation for an IPv4 address."""
    # This regex is simple and covers most common cases.
    pattern = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
    if not pattern.match(ip):
        return False
    parts = ip.split('.')
    for part in parts:
        if not 0 <= int(part) <= 255:
            return False
    return True

def update_ip_address(engine, arduino_id, ip_address):
    """Updates the arduino_ip for a given lamp in the database."""
    query = text("""
        UPDATE lamps 
        SET arduino_ip = :ip_address 
        WHERE arduino_id = :arduino_id
    """)
    
    try:
        with engine.connect() as conn:
            # First, check if the arduino_id exists
            check_query = text("SELECT COUNT(*) FROM lamps WHERE arduino_id = :arduino_id")
            result = conn.execute(check_query, {"arduino_id": arduino_id})
            count = result.scalar()
            
            if count == 0:
                print(f"⚠️  WARNING: No lamp found with Arduino ID: {arduino_id}")
                return False

            # If it exists, perform the update
            result = conn.execute(query, {"ip_address": ip_address, "arduino_id": arduino_id})
            conn.commit()
            
            # Check if any rows were actually changed
            if result.rowcount > 0:
                print(f"✅ Successfully updated Arduino {arduino_id} with IP {ip_address}")
                return True
            else:
                # This case is unlikely if the check passes, but good practice
                print(f"🤔 No rows were updated. Is the Arduino ID {arduino_id} correct?")
                return False

    except Exception as e:
        print(f"❌ ERROR: Database update failed: {e}")
        return False

def main():
    """Main function to run the interactive script."""
    print("--- Surf Lamp IP Address Updater ---")
    
    engine = get_db_engine()
    if not engine:
        return

    while True:
        try:
            # --- Get Arduino ID ---
            id_input = input("Enter the Arduino ID to update (e.g., 4433): ")
            if not id_input:
                print("No input provided. Exiting.")
                break
            arduino_id = int(id_input)

            # --- Get IP Address ---
            ip_input = input(f"Enter the new IP address for Arduino {arduino_id}: ")
            if not ip_input:
                print("No input provided. Exiting.")
                break
            
            if not is_valid_ip(ip_input):
                print(f"❌ ERROR: '{ip_input}' is not a valid IP address. Please try again.")
                print("---")
                continue

            # --- Confirm and Update ---
            confirm = input(f"Update Arduino ID {arduino_id} with IP {ip_input}? (y/n): ").lower()
            if confirm == 'y':
                update_ip_address(engine, arduino_id, ip_input)
            else:
                print("Update cancelled.")

            # --- Ask to continue ---
            another = input("Update another device? (y/n): ").lower()
            if another != 'y':
                print("Exiting program. Goodbye!")
                break
            print("---")

        except ValueError:
            print("❌ ERROR: Invalid input. Arduino ID must be a number. Please start over.")
            print("---")
            continue
        except (KeyboardInterrupt, EOFError):
            print("nExiting program. Goodbye!")
            break

if __name__ == "__main__":
    main()
