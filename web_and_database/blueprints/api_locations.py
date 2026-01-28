'''
future optimization:
when there will be more than 50k lamps
purpose: an api end point for fetching surf conditions by locations
instead of lamps goidg every minute to the render service end point
they will fetch it from a proxy server CDN that the render service will update that way 1500 lamps all get there
data from the CDN and not from the render service
only works cause the values for a certain location is the same for all the lmaps in that location 
it doesnt work for personal settings or any personalized data
'''

import logging
import sys
import os
from flask import Blueprint, make_response
from data_base import SessionLocal, Location
from utils.helpers import get_sunset_info_cached

# Add processor path to import sunset calculator
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
processor_path = os.path.join(os.path.dirname(parent_dir), 'surf-lamp-processor')
sys.path.insert(0, processor_path)
from sunset_calculator import get_sunset_info

logger = logging.getLogger(__name__)

bp = Blueprint('api_locations', __name__)


@bp.route("/api/locations/<path:location>/conditions", methods=['GET'])
def get_location_conditions(location):
    """
    PUBLIC ENDPOINT - CDN Cacheable
    Returns current surf conditions for a location (shared by all lamps at that location).

    This endpoint is designed for CDN caching to reduce bandwidth costs at scale.
    Cache-Control: public, max-age=300 (5 minutes)

    Response includes:
    - Wave height, period
    - Wind speed, direction
    - Sunset animation trigger
    - Last updated timestamp

    Architecture:
    - At 50K+ lamps: Route through CDN (Cloudflare)
    - CDN caches for 5 minutes → reduces server hits by 75%
    - One location update serves ALL lamps at that location
    """
    logger.info(f"📍 Location conditions requested for: {location}")

    try:
        db = SessionLocal()
        try:
            # Query location data
            location_data = db.query(Location).filter(Location.location == location).first()

            if not location_data:
                logger.warning(f"⚠️ Location '{location}' not found in database")
                return {'error': f'Location {location} not found'}, 404

            # Calculate sunset info for this location (cached per location, expires every 24h)
            sunset_info = get_sunset_info_cached(location, get_sunset_info, trigger_window_minutes=15)

            # Build public response (no user-specific data)
            conditions = {
                'location': location,
                'wave_height_cm': int(round((location_data.wave_height_m or 0) * 100)),
                'wave_period_s': location_data.wave_period_s or 0.0,
                'wind_speed_mps': int(round(location_data.wind_speed_mps or 0)),
                'wind_direction_deg': location_data.wind_direction_deg or 0,
                'sunset_animation': sunset_info['sunset_trigger'],
                'day_of_year': sunset_info['day_of_year'],
                'last_updated': location_data.last_updated.isoformat() if location_data.last_updated else '1970-01-01T00:00:00Z',
                'data_available': bool(location_data.wave_height_m or location_data.wind_speed_mps)
            }

            logger.info(f"✅ Returning public conditions for {location}: wave={conditions['wave_height_cm']}cm")

            # Add CDN-friendly cache headers
            response = make_response(conditions, 200)
            response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes
            response.headers['Vary'] = 'Accept-Encoding'  # Support compression

            return response

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting conditions for location {location}: {e}")
        return {'error': 'Server error'}, 500
