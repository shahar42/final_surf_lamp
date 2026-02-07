"""
Beach service layer for location operations.
Handles validation, coordinate lookup, and API URL generation.

Author: shahar nitzan
"""

import os
from typing import Optional, Tuple
from .beaches import get_beach_by_name


def is_valid_beach(name: str) -> bool:
    """Check if a beach name is valid."""
    return get_beach_by_name(name) is not None


def get_beach_coordinates(name: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a beach.
    Returns: (latitude, longitude) or None if beach not found.
    """
    beach = get_beach_by_name(name)
    if beach:
        return (beach["latitude"], beach["longitude"])
    return None


def generate_wave_api_url(lat: float, lng: float) -> str:
    """
    Generate wave API URL from coordinates.
    Uses Open-Meteo Marine API.
    """
    return (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={lat}&longitude={lng}"
        f"&hourly=wave_height,wave_period"
        f"&timezone=auto"
    )


def generate_wind_api_url(lat: float, lng: float) -> str:
    """
    Generate wind API URL from coordinates.
    Uses Open-Meteo API.

    CRITICAL: Must include wind_speed_unit=ms for processor validation.
    """
    return (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lng}"
        f"&hourly=wind_speed_10m,wind_direction_10m"
        f"&wind_speed_unit=ms"
        f"&timezone=auto"
    )


def get_api_urls_for_beach(name: str) -> Optional[Tuple[str, str]]:
    """
    Get wave and wind API URLs for a beach.
    Returns: (wave_url, wind_url) or None if beach not found.
    """
    coords = get_beach_coordinates(name)
    if not coords:
        return None
    
    lat, lng = coords
    return (
        generate_wave_api_url(lat, lng),
        generate_wind_api_url(lat, lng)
    )


# Mapping from old city locations to default beach
CITY_TO_BEACH_MAPPING = {
    "Haifa, Israel": "Bat Galim (Haifa)",
    "Tel Aviv, Israel": "Hilton Beach (Tel Aviv)",
    "Ashdod, Israel": "Ashdod (Gil Beach)",
    "Netanya, Israel": "Sironit Beach (Netanya)",
    "Hadera, Israel": "Olga Beach (Hadera)",
    "Ashkelon, Israel": "Ashkelon (Marina)",
    "Nahariya, Israel": "Sokolov Beach (Nahariya)",
    "Eilat, Israel": "Zikim Beach",  # Closest available (no Eilat beaches in list)
}


def migrate_city_to_beach(city_location: str) -> str:
    """
    Map an old city-based location to a beach.
    Falls back to Hilton Beach if no mapping found.
    """
    return CITY_TO_BEACH_MAPPING.get(city_location, "Hilton Beach (Tel Aviv)")
