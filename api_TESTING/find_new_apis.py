import requests
import json
from typing import List, Dict, Any, Set
import concurrent.futures
import logging
import configparser
import re
import time
import os
from urllib.parse import urljoin

# --- Configuration ---

def load_config(config_file: str = "config.ini") -> Dict[str, Any]:
    """
    Loads configuration from a config file or sets defaults if not found.

    Args:
        config_file: Path to the configuration file.

    Returns:
        Dictionary containing configuration settings.
    """
    config = configparser.ConfigParser()
    defaults = {
        "endpoints": [
            "https://marine-api.open-meteo.com/v1/marine?latitude=33.7&longitude=-118.2&hourly=wave_height,wave_period",
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station={station_id}&product=water_level&datum=MLLW&units=metric&time_zone=gmt&format=json"
        ],
        "stations": ["9410660", "9415144", "9414523", "9414290"],
        "keywords": {
            "wind_speed": "WSPD,wind_speed,windSpeed,wind-speed",
            "wave_height": "WVHT,wave_height,waveHeight,wave-height",
            "wave_period": "DPD,dominant_wave_period,wavePeriod,wave_period",
            "water_temp": "WTMP,water_temp,waterTemp,water-temperature",
            "air_temp": "ATMP,air_temp,airTemp,air-temperature"
        },
        "max_concurrent_requests": 10,
        "request_timeout": 10,
        "max_retries": 3,
        "retry_delay": 2,
        "output_file": "valid_marine_apis.json",
        "discovery_urls": [
            "https://www.ndbc.noaa.gov/",
            "https://api.tidesandcurrents.noaa.gov/"
        ]
    }

    if os.path.exists(config_file):
        config.read(config_file)
        return {
            "endpoints": config.get("Settings", "endpoints", fallback=','.join(defaults["endpoints"])).split(","),
            "stations": config.get("Settings", "stations", fallback=','.join(defaults["stations"])).split(","),
            "keywords": {
                key: set(config.get("Keywords", key, fallback=value).split(","))
                for key, value in defaults["keywords"].items()
            },
            "max_concurrent_requests": config.getint("Settings", "max_concurrent_requests", fallback=defaults["max_concurrent_requests"]),
            "request_timeout": config.getint("Settings", "request_timeout", fallback=defaults["request_timeout"]),
            "max_retries": config.getint("Settings", "max_retries", fallback=defaults["max_retries"]),
            "retry_delay": config.getint("Settings", "retry_delay", fallback=defaults["retry_delay"]),
            "output_file": config.get("Settings", "output_file", fallback=defaults["output_file"]),
            "discovery_urls": config.get("Settings", "discovery_urls", fallback=','.join(defaults["discovery_urls"])).split(",")
        }
    return defaults

# --- Setup Logging ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("marine_api_discovery.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Core Discovery and Validation Functions ---

def discover_endpoints(session: requests.Session, base_urls: List[str]) -> List[str]:
    """
    Attempts to discover JSON API endpoints by crawling base URLs or testing common patterns.

    Args:
        session: The requests session object.
        base_urls: List of base URLs to explore.

    Returns:
        List of potential JSON endpoint URLs.
    """
    potential_endpoints = []
    common_api_paths = [
        "api/v1/data",
        "data/json",
        "v1/stations",
        "api/prod/datagetter",
        "v1/marine"
    ]

    for base_url in base_urls:
        for path in common_api_paths:
            test_url = urljoin(base_url, path)
            try:
                response = session.head(test_url, timeout=5, allow_redirects=True)
                if response.status_code == 200 and "json" in response.headers.get("Content-Type", "").lower():
                    potential_endpoints.append(test_url)
                    logger.info(f"Discovered potential JSON endpoint: {test_url}")
            except requests.exceptions.RequestException:
                continue

    return potential_endpoints

def search_data_for_keywords(data: Any, keywords: Set[str]) -> bool:
    """
    Recursively searches through a nested data structure for any keywords using case-insensitive partial matching.

    Args:
        data: The data to search (dict, list, str, or primitive).
        keywords: A set of keywords to look for.

    Returns:
        True if any keyword is found, False otherwise.
    """
    def contains_keyword(text: str) -> bool:
        text_lower = text.lower()
        return any(re.search(rf'\b{re.escape(keyword.lower())}\b', text_lower) for keyword in keywords)

    if isinstance(data, dict):
        for key, value in data.items():
            if contains_keyword(key) or (isinstance(value, str) and contains_keyword(value)):
                return True
            if search_data_for_keywords(value, keywords):
                return True
    elif isinstance(data, list):
        for item in data:
            if search_data_for_keywords(item, keywords):
                return True
    elif isinstance(data, str):
        return contains_keyword(data)
    return False

def validate_endpoint(session: requests.Session, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempts to retrieve and validate JSON data from a given URL with retries.

    Args:
        session: The requests session object.
        url: The URL of the potential API endpoint.
        config: Configuration dictionary with keywords and settings.

    Returns:
        Dictionary containing validation status and found parameters.
    """
    result = {
        "url": url,
        "is_valid": False,
        "found_params": [],
        "format": "json",
        "error": None
    }

    for attempt in range(config["max_retries"]):
        try:
            # Quick HEAD request to check if endpoint exists
            head_response = session.head(url, timeout=config["request_timeout"], allow_redirects=True)
            if head_response.status_code != 200:
                result["error"] = f"Endpoint not found (HTTP {head_response.status_code})"
                return result

            response = session.get(url, timeout=config["request_timeout"])
            response.raise_for_status()

            # Check if response is JSON
            content_type = response.headers.get("Content-Type", "").lower()
            if "json" not in content_type:
                result["error"] = f"Response is not JSON, received: {content_type}"
                return result

            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                result["error"] = f"Invalid JSON: {str(e)}"
                return result

            # Validate required parameters
            found_all = True
            for param, keywords in config["keywords"].items():
                if search_data_for_keywords(data, keywords):
                    result["found_params"].append(param)
                else:
                    found_all = False

            if found_all:
                result["is_valid"] = True
            break
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            if attempt < config["max_retries"] - 1:
                logger.warning(f"Retrying {url} (attempt {attempt + 2}/{config['max_retries']}) after error: {str(e)}")
                time.sleep(config["retry_delay"])
            else:
                logger.error(f"Failed to validate {url} after {config['max_retries']} attempts: {str(e)}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for {url}: {str(e)}")
            break

    return result

def save_valid_apis(valid_apis: List[Dict[str, Any]], filename: str):
    """
    Saves the list of validated APIs to a JSON file.

    Args:
        valid_apis: List of dictionaries representing valid APIs.
        filename: The name of the file to save results to.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(valid_apis, f, indent=4)
        logger.info(f"Saved {len(valid_apis)} valid JSON API endpoints to {filename}")
    except Exception as e:
        logger.error(f"Failed to save valid APIs to {filename}: {str(e)}")

# --- Main Execution ---

def main():
    logger.info("Starting Marine JSON API Discovery")
    config = load_config()

    # Discover additional endpoints
    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Marine-JSON-API-Discovery-Tool/2.1'})
        discovered_endpoints = discover_endpoints(session, config["discovery_urls"])
        logger.info(f"Found {len(discovered_endpoints)} additional endpoints via discovery")

    # Prepare endpoints
    endpoints_to_test = []
    for endpoint_template in config["endpoints"] + discovered_endpoints:
        if "{station_id}" in endpoint_template:
            for station in config["stations"]:
                endpoints_to_test.append(endpoint_template.format(station_id=station))
        else:
            endpoints_to_test.append(endpoint_template)

    logger.info(f"Total {len(endpoints_to_test)} endpoints to test")

    # Validate endpoints concurrently
    valid_apis = []
    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Marine-JSON-API-Discovery-Tool/2.1'})
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["max_concurrent_requests"]) as executor:
            future_to_url = {executor.submit(validate_endpoint, session, url, config): url for url in endpoints_to_test}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result["is_valid"]:
                        logger.info(f"[SUCCESS] {url} - Found parameters: {', '.join(result['found_params'])} (Format: JSON)")
                        valid_apis.append(result)
                    else:
                        reason = result["error"] or f"Missing required parameters. Found: {result['found_params']}"
                        logger.warning(f"[FAILURE] {url} - {reason}")
                except Exception as e:
                    logger.error(f"Error processing {url}: {str(e)}")

    if valid_apis:
        save_valid_apis(valid_apis, config["output_file"])
    else:
        logger.info("No valid JSON API endpoints found")
        logger.info("Suggestions: Check https://www.ndbc.noaa.gov/ or https://api.tidesandcurrents.noaa.gov/ for JSON API documentation, or add new endpoints to config.ini")

if __name__ == "__main__":
    main()
