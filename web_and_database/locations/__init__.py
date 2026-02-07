# Location module for beach-based locations
from .beaches import (
    ALL_BEACHES,
    get_all_beaches,
    get_beach_by_name,
    search_beaches,
    get_all_beach_names
)
from .beach_service import (
    is_valid_beach,
    get_beach_coordinates,
    generate_wave_api_url,
    generate_wind_api_url
)

__all__ = [
    'ALL_BEACHES',
    'get_all_beaches',
    'get_beach_by_name',
    'search_beaches',
    'get_all_beach_names',
    'is_valid_beach',
    'get_beach_coordinates',
    'generate_wave_api_url',
    'generate_wind_api_url'
]
