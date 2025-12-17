from datetime import datetime, timezone

# Location change rate limiting storage
location_changes = {}  # {user_id: [timestamp1, timestamp2, ...]}

def check_location_change_limit(user_id):
    """Check if user has exceeded 5 location changes per day"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if user_id not in location_changes:
        location_changes[user_id] = []
    
    # Remove old entries (older than 24 hours)
    location_changes[user_id] = [
        timestamp for timestamp in location_changes[user_id] 
        if timestamp > today_start
    ]
    
    # Check if limit exceeded (more than 5 changes)
    if len(location_changes[user_id]) >= 5:
        return False
        
    return True

def record_location_change(user_id):
    """Record a location change for the user"""
    if user_id not in location_changes:
        location_changes[user_id] = []
    location_changes[user_id].append(datetime.now(timezone.utc))
