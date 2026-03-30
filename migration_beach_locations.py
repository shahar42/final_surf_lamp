"""
Migration script: Beach Locations

Creates Location records for all beaches and migrates existing
users from city-based locations to beach-based locations.

Run: python migration_beach_locations.py

Author: shahar nitzan
"""

import sys
import os

# Add web_and_database to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_and_database'))

from data_base import SessionLocal, Location, User, Arduino
from locations import get_all_beaches
from locations.beach_service import (
    get_api_urls_for_beach,
    migrate_city_to_beach,
    CITY_TO_BEACH_MAPPING
)


def create_beach_locations(db):
    """Create Location records for all beaches."""
    beaches = get_all_beaches()
    created = 0
    skipped = 0
    
    for beach in beaches:
        name = beach['english_name']
        
        # Check if already exists
        existing = db.query(Location).filter(Location.location == name).first()
        if existing:
            print(f"  [SKIP] {name} - already exists")
            skipped += 1
            continue
        
        # Get API URLs
        urls = get_api_urls_for_beach(name)
        if not urls:
            print(f"  [ERROR] {name} - failed to generate API URLs")
            continue
        
        wave_url, wind_url = urls
        
        # Create location
        location = Location(
            location=name,
            wave_api_url=wave_url,
            wind_api_url=wind_url
        )
        db.add(location)
        print(f"  [CREATE] {name}")
        created += 1
    
    db.commit()
    return created, skipped


def migrate_users(db, dry_run=False):
    """Migrate users from city locations to beach locations."""
    migrated = 0
    errors = 0
    
    # Find users with old city-based locations
    old_locations = list(CITY_TO_BEACH_MAPPING.keys())
    users = db.query(User).filter(User.location.in_(old_locations)).all()
    
    print(f"\nFound {len(users)} users with city-based locations")
    
    for user in users:
        old_location = user.location
        new_location = migrate_city_to_beach(old_location)
        
        if dry_run:
            print(f"  [DRY-RUN] {user.username}: {old_location} -> {new_location}")
        else:
            try:
                user.location = new_location
                print(f"  [MIGRATE] {user.username}: {old_location} -> {new_location}")
                migrated += 1
            except Exception as e:
                print(f"  [ERROR] {user.username}: {e}")
                errors += 1
    
    if not dry_run:
        db.commit()
    
    return migrated, errors


def migrate_arduinos(db, dry_run=False):
    """Migrate arduino locations from city to beach."""
    migrated = 0
    
    old_locations = list(CITY_TO_BEACH_MAPPING.keys())
    arduinos = db.query(Arduino).filter(Arduino.location.in_(old_locations)).all()
    
    print(f"\nFound {len(arduinos)} arduinos with city-based locations")
    
    for arduino in arduinos:
        old_location = arduino.location
        new_location = migrate_city_to_beach(old_location)
        
        if dry_run:
            print(f"  [DRY-RUN] Arduino #{arduino.arduino_id}: {old_location} -> {new_location}")
        else:
            arduino.location = new_location
            print(f"  [MIGRATE] Arduino #{arduino.arduino_id}: {old_location} -> {new_location}")
            migrated += 1
    
    if not dry_run:
        db.commit()
    
    return migrated


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Migrate to beach-based locations')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Beach Locations Migration")
    print("=" * 60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    
    db = SessionLocal()
    
    try:
        # Step 1: Create beach locations
        print("\n[1/3] Creating beach locations...")
        created, skipped = create_beach_locations(db)
        print(f"  Created: {created}, Skipped: {skipped}")
        
        # Step 2: Migrate users
        print("\n[2/3] Migrating user locations...")
        user_migrated, user_errors = migrate_users(db, dry_run=args.dry_run)
        print(f"  Migrated: {user_migrated}, Errors: {user_errors}")
        
        # Step 3: Migrate arduinos
        print("\n[3/3] Migrating arduino locations...")
        arduino_migrated = migrate_arduinos(db, dry_run=args.dry_run)
        print(f"  Migrated: {arduino_migrated}")
        
        print("\n" + "=" * 60)
        print("Migration complete!")
        print("=" * 60)
        
    finally:
        db.close()


if __name__ == '__main__':
    main()
