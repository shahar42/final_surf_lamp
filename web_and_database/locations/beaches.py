"""
Beach location data with coordinates.
Replaces city-based SURF_LOCATIONS with specific beach locations.
Supports beaches worldwide with timezone information.

Author: shahar nitzan
"""

from typing import List, Dict, Optional

# Legacy city mapping removed - all locations use beach-specific names now

# Global beach data with region and timezone metadata
ALL_BEACHES: List[Dict] = [
    # North Coast
    {"english_name": "Achziv Beach", "hebrew_name": "חוף אכזיב", "latitude": 33.0536, "longitude": 35.2714, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Nahariya"]},
    {"english_name": "Betzet Beach", "hebrew_name": "חוף בצת", "latitude": 32.9750, "longitude": 35.1650, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Nahariya"]},
    {"english_name": "Shavei Tzion", "hebrew_name": "שבי ציון", "latitude": 33.0278, "longitude": 35.2572, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Nahariya"]},
    {"english_name": "Sokolov Beach (Nahariya)", "hebrew_name": "חוף סוקולוב", "latitude": 32.9892, "longitude": 35.2431, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Nahariya"]},
    {"english_name": "Kiryat Yam", "hebrew_name": "קריית ים", "latitude": 32.9533, "longitude": 35.2125, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Haifa"]},
    {"english_name": "Bat Galim (Haifa)", "hebrew_name": "בת גלים", "latitude": 32.8242, "longitude": 34.9897, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Haifa"]},
    {"english_name": "Backdoor (Haifa)", "hebrew_name": "בקדור", "latitude": 32.8300, "longitude": 34.9800, "region": "North Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "North Coast", "Haifa"]},

    # Central Coast
    {"english_name": "Atlit Beach", "hebrew_name": "חוף עתלית", "latitude": 32.7211, "longitude": 34.9433, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Atlit"]},
    {"english_name": "Caesarea (Arches)", "hebrew_name": "קיסריה (הקשתות)", "latitude": 32.5014, "longitude": 34.8936, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Caesarea"]},
    {"english_name": "Sdot Yam", "hebrew_name": "שדות ים", "latitude": 32.4425, "longitude": 34.8683, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Caesarea"]},
    {"english_name": "Beit Yanai", "hebrew_name": "בית ינאי", "latitude": 32.4078, "longitude": 34.8425, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Netanya"]},
    {"english_name": "Kontiki Beach (Netanya)", "hebrew_name": "חוף קונטיקי", "latitude": 32.3333, "longitude": 34.8450, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Netanya"]},
    {"english_name": "Sironit Beach (Netanya)", "hebrew_name": "חוף סירונית", "latitude": 32.3272, "longitude": 34.8422, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Netanya"]},
    {"english_name": "Poleg Beach", "hebrew_name": "חוף פולג", "latitude": 32.2750, "longitude": 34.8350, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Netanya"]},
    {"english_name": "Olga Beach (Hadera)", "hebrew_name": "חוף גבעת אולגה", "latitude": 32.4355, "longitude": 34.8850, "region": "Central Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "Central Coast", "Hadera"]},

    # Tel Aviv Metropolitan
    {"english_name": "Zvulun Beach (Herzliya)", "hebrew_name": "חוף זבולון", "latitude": 32.1750, "longitude": 34.7850, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv", "Herzliya"]},
    {"english_name": "Herzliya Marina", "hebrew_name": "מרינה הרצליה", "latitude": 32.1620, "longitude": 34.7950, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv", "Herzliya"]},
    {"english_name": "Tel Baruch Beach", "hebrew_name": "חוף תל ברוך", "latitude": 32.1233, "longitude": 34.7767, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv"]},
    {"english_name": "Hilton Beach (Tel Aviv)", "hebrew_name": "חוף הילטון", "latitude": 32.0910, "longitude": 34.7710, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv"]},
    {"english_name": "Gordon Beach (Tel Aviv)", "hebrew_name": "חוף גורדון", "latitude": 32.0833, "longitude": 34.7680, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv"]},
    {"english_name": "Maravi Beach (Tel Aviv)", "hebrew_name": "החוף המערבי", "latitude": 32.0580, "longitude": 34.7590, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv"]},
    {"english_name": "Bat Yam (Main Beach)", "hebrew_name": "חוף בת ים", "latitude": 32.0167, "longitude": 34.7333, "region": "Tel Aviv Metro", "country": "Israel", "tags": ["Israel", "Mediterranean", "Tel Aviv", "Bat Yam"]},

    # South Coast
    {"english_name": "Palmachim Beach", "hebrew_name": "חוף פלמחים", "latitude": 31.9300, "longitude": 34.6950, "region": "South Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "South Coast"]},
    {"english_name": "Ashdod (Gil Beach)", "hebrew_name": "חוף גיל", "latitude": 31.8120, "longitude": 34.6380, "region": "South Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "South Coast", "Ashdod"]},
    {"english_name": "Ashdod (Kshatot)", "hebrew_name": "חוף הקשתות", "latitude": 31.7939, "longitude": 34.6328, "region": "South Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "South Coast", "Ashdod"]},
    {"english_name": "Ashkelon (Marina)", "hebrew_name": "מרינה אשקלון", "latitude": 31.6833, "longitude": 34.5567, "region": "South Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "South Coast", "Ashkelon"]},
    {"english_name": "Zikim Beach", "hebrew_name": "חוף זיקים", "latitude": 31.6167, "longitude": 34.4850, "region": "South Coast", "country": "Israel", "tags": ["Israel", "Mediterranean", "South Coast"]},

    # Hawaii - Oahu
    {"english_name": "Waikiki Beach (Honolulu)", "hebrew_name": "Waikiki Beach (Honolulu)", "latitude": 21.2820, "longitude": -157.8310, "region": "Oahu", "country": "USA", "timezone": "Pacific/Honolulu", "tags": ["Hawaii", "USA", "Pacific", "Oahu", "Honolulu"]},
    {"english_name": "Waimea Bay Beach (North Shore)", "hebrew_name": "Waimea Bay Beach (North Shore)", "latitude": 21.6397, "longitude": -158.0574, "region": "Oahu", "country": "USA", "timezone": "Pacific/Honolulu", "tags": ["Hawaii", "USA", "Pacific", "Oahu", "North Shore"]},
    {"english_name": "Lanikai Beach (Kailua)", "hebrew_name": "Lanikai Beach (Kailua)", "latitude": 21.4005, "longitude": -157.7167, "region": "Oahu", "country": "USA", "timezone": "Pacific/Honolulu", "tags": ["Hawaii", "USA", "Pacific", "Oahu", "Kailua"]},
]

# Build lookup dict for fast access
_BEACH_BY_NAME: Dict[str, Dict] = {beach["english_name"]: beach for beach in ALL_BEACHES}


def get_all_beaches() -> List[Dict]:
    """Return all beach data."""
    return ALL_BEACHES


def get_all_beach_names() -> List[str]:
    """Return list of all beach names (for backward compatibility with SURF_LOCATIONS)."""
    return [beach["english_name"] for beach in ALL_BEACHES]


def get_beach_by_name(name: str) -> Optional[Dict]:
    """Get beach data by English name (case-insensitive)."""
    # Exact match first
    if name in _BEACH_BY_NAME:
        return _BEACH_BY_NAME[name]
    
    # Case-insensitive fallback
    name_lower = name.lower()
    for beach in ALL_BEACHES:
        if beach["english_name"].lower() == name_lower:
            return beach

    return None


def search_beaches(query: str, limit: int = 10) -> List[Dict]:
    """
    Search beaches by English name, Hebrew name, region, or tags.
    Returns matches sorted by relevance (starts-with > contains > tag matches).

    Examples:
        "Israel" -> All 27 Israeli beaches
        "Tel Aviv" -> All Tel Aviv Metro beaches
        "Hilton" -> Hilton Beach (Tel Aviv)
        "Mediterranean" -> All Mediterranean beaches
        "Hadera, Israel" -> Olga Beach (Hadera) [legacy city mapping]
    """
    if not query or len(query) < 1:
        return ALL_BEACHES[:limit]

    query_lower = query.lower()
    starts_with = []
    contains = []
    tag_matches = []
    seen = set()  # Track beaches we've already matched

    for beach in ALL_BEACHES:
        beach_id = beach["english_name"]
        english_lower = beach["english_name"].lower()
        hebrew = beach["hebrew_name"]

        # Priority 1: Starts-with match on English name
        if english_lower.startswith(query_lower):
            starts_with.append(beach)
            seen.add(beach_id)
        # Priority 2: Contains match on English or Hebrew name
        elif query_lower in english_lower or query in hebrew:
            contains.append(beach)
            seen.add(beach_id)
        # Priority 3: Tag/region matches (region-aware discovery)
        elif beach_id not in seen:
            # Check region
            if query_lower in beach.get("region", "").lower():
                tag_matches.append(beach)
                seen.add(beach_id)
            # Check country
            elif query_lower in beach.get("country", "").lower():
                tag_matches.append(beach)
                seen.add(beach_id)
            # Check tags
            elif any(query_lower in tag.lower() for tag in beach.get("tags", [])):
                tag_matches.append(beach)
                seen.add(beach_id)

    # Combine: starts-with > contains > tag matches
    results = starts_with + contains + tag_matches
    return results[:limit]
