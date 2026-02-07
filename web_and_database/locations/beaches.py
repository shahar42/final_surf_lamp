"""
Israeli beach data with coordinates.
Replaces city-based SURF_LOCATIONS with specific beach locations.

Author: shahar nitzan
"""

from typing import List, Dict, Optional

# Beach data from israel_beaches.md
ISRAEL_BEACHES: List[Dict] = [
    {"english_name": "Achziv Beach", "hebrew_name": "חוף אכזיב", "latitude": 33.0536, "longitude": 35.2714},
    {"english_name": "Betzet Beach", "hebrew_name": "חוף בצת", "latitude": 32.9750, "longitude": 35.1650},
    {"english_name": "Shavei Tzion", "hebrew_name": "שבי ציון", "latitude": 33.0278, "longitude": 35.2572},
    {"english_name": "Sokolov Beach (Nahariya)", "hebrew_name": "חוף סוקולוב", "latitude": 32.9892, "longitude": 35.2431},
    {"english_name": "Kiryat Yam", "hebrew_name": "קריית ים", "latitude": 32.9533, "longitude": 35.2125},
    {"english_name": "Bat Galim (Haifa)", "hebrew_name": "בת גלים", "latitude": 32.8242, "longitude": 34.9897},
    {"english_name": "Backdoor (Haifa)", "hebrew_name": "בקדור", "latitude": 32.8300, "longitude": 34.9800},
    {"english_name": "Atlit Beach", "hebrew_name": "חוף עתלית", "latitude": 32.7211, "longitude": 34.9433},
    {"english_name": "Caesarea (Arches)", "hebrew_name": "קיסריה (הקשתות)", "latitude": 32.5014, "longitude": 34.8936},
    {"english_name": "Sdot Yam", "hebrew_name": "שדות ים", "latitude": 32.4425, "longitude": 34.8683},
    {"english_name": "Beit Yanai", "hebrew_name": "בית ינאי", "latitude": 32.4078, "longitude": 34.8425},
    {"english_name": "Kontiki Beach (Netanya)", "hebrew_name": "חוף קונטיקי", "latitude": 32.3333, "longitude": 34.8450},
    {"english_name": "Sironit Beach (Netanya)", "hebrew_name": "חוף סירונית", "latitude": 32.3272, "longitude": 34.8422},
    {"english_name": "Poleg Beach", "hebrew_name": "חוף פולג", "latitude": 32.2750, "longitude": 34.8350},
    {"english_name": "Zvulun Beach (Herzliya)", "hebrew_name": "חוף זבולון", "latitude": 32.1750, "longitude": 34.7850},
    {"english_name": "Herzliya Marina", "hebrew_name": "מרינה הרצליה", "latitude": 32.1620, "longitude": 34.7950},
    {"english_name": "Tel Baruch Beach", "hebrew_name": "חוף תל ברוך", "latitude": 32.1233, "longitude": 34.7767},
    {"english_name": "Hilton Beach (Tel Aviv)", "hebrew_name": "חוף הילטון", "latitude": 32.0910, "longitude": 34.7710},
    {"english_name": "Gordon Beach (Tel Aviv)", "hebrew_name": "חוף גורדון", "latitude": 32.0833, "longitude": 34.7680},
    {"english_name": "Maravi Beach (Tel Aviv)", "hebrew_name": "החוף המערבי", "latitude": 32.0580, "longitude": 34.7590},
    {"english_name": "Bat Yam (Main Beach)", "hebrew_name": "חוף בת ים", "latitude": 32.0167, "longitude": 34.7333},
    {"english_name": "Palmachim Beach", "hebrew_name": "חוף פלמחים", "latitude": 31.9300, "longitude": 34.6950},
    {"english_name": "Ashdod (Gil Beach)", "hebrew_name": "חוף גיל", "latitude": 31.8120, "longitude": 34.6380},
    {"english_name": "Ashdod (Kshatot)", "hebrew_name": "חוף הקשתות", "latitude": 31.7939, "longitude": 34.6328},
    {"english_name": "Ashkelon (Marina)", "hebrew_name": "מרינה אשקלון", "latitude": 31.6833, "longitude": 34.5567},
    {"english_name": "Zikim Beach", "hebrew_name": "חוף זיקים", "latitude": 31.6167, "longitude": 34.4850},
    {"english_name": "Olga Beach (Hadera)", "hebrew_name": "חוף גבעת אולגה", "latitude": 32.4355, "longitude": 34.8850},
]

# Build lookup dict for fast access
_BEACH_BY_NAME: Dict[str, Dict] = {beach["english_name"]: beach for beach in ISRAEL_BEACHES}


def get_all_beaches() -> List[Dict]:
    """Return all beach data."""
    return ISRAEL_BEACHES


def get_all_beach_names() -> List[str]:
    """Return list of all beach names (for backward compatibility with SURF_LOCATIONS)."""
    return [beach["english_name"] for beach in ISRAEL_BEACHES]


def get_beach_by_name(name: str) -> Optional[Dict]:
    """Get beach data by English name (case-insensitive)."""
    # Exact match first
    if name in _BEACH_BY_NAME:
        return _BEACH_BY_NAME[name]
    
    # Case-insensitive fallback
    name_lower = name.lower()
    for beach in ISRAEL_BEACHES:
        if beach["english_name"].lower() == name_lower:
            return beach
    
    return None


def search_beaches(query: str, limit: int = 10) -> List[Dict]:
    """
    Search beaches by English or Hebrew name.
    Returns matches sorted by relevance (starts-with > contains).
    """
    if not query or len(query) < 1:
        return ISRAEL_BEACHES[:limit]
    
    query_lower = query.lower()
    starts_with = []
    contains = []
    
    for beach in ISRAEL_BEACHES:
        english_lower = beach["english_name"].lower()
        hebrew = beach["hebrew_name"]
        
        # Check English name
        if english_lower.startswith(query_lower):
            starts_with.append(beach)
        elif query_lower in english_lower:
            contains.append(beach)
        # Check Hebrew name
        elif query in hebrew:
            contains.append(beach)
    
    # Combine: starts-with matches first, then contains
    results = starts_with + contains
    return results[:limit]
