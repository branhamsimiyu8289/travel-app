# a weather travel application
"""
Travel Weather & GPS Intelligence Tool
---------------------------------------
Finds all matching places with exact GPS coordinates (latitude, longitude),
retrieves precise weather data for the selected coordinates, and merges it
with country demographic and geographic data from the REST Countries API.

Usage:
    python day3_travel_info.py

Requirements:
    pip install requests python-dotenv
    OPENWEATHER_API_KEY in .env file
    RESTCOUNTRIES_API_KEY in .env file
"""
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

# Ensure console supports UTF-8 characters on all platforms (including Windows cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (LookupError, OSError, ValueError) as error:
        print(
            f"Warning: UTF-8 console encoding could not be configured: {error}",
            file=sys.stderr,
        )

load_dotenv()

api_key = os.getenv("OPENWEATHER_API_KEY")
restcountries_api_key = os.getenv("RESTCOUNTRIES_API_KEY")

HTTP_STATUS_EXPLANATIONS = {
    200: "The request succeeded and data was returned.",
    400: "The request was invalid. Check the city name or coordinates.",
    401: "The API key is missing, invalid, or not authorized for this service.",
    404: "The requested location or country was not found.",
    429: "The API rate limit was reached. Wait before trying again.",
    500: "The API service encountered an internal error. Try again later.",
}


class APIResponseError(Exception):
    """An HTTP error response from one of the external APIs."""

    def __init__(self, service: str, status_code: int):
        self.service = service
        self.status_code = status_code
        explanation = HTTP_STATUS_EXPLANATIONS.get(
            status_code,
            "The API returned an unexpected HTTP error. Try again later.",
        )
        super().__init__(f"{service} returned HTTP {status_code}: {explanation}")


def check_api_response(response: requests.Response, service: str) -> None:
    """Accepts HTTP 200 and turns all other statuses into explanatory errors."""
    if response.status_code != 200:
        raise APIResponseError(service, response.status_code)


def parse_coordinates(query: str) -> Optional[Tuple[float, float]]:
    """
    Parses a string if the user entered GPS coordinates like:
    '51.5074, -0.1278' or '-1.286389, 36.817223'.
    Returns (lat, lon) tuple or None if input is a name.
    """
    match = re.match(
        r"^\s*([-+]?\d+(?:\.\d+)?)\s*[, ]\s*([-+]?\d+(?:\.\d+)?)\s*$",
        query.strip(),
    )
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            return lat, lon
    return None


def is_coordinate_pair(query: str) -> bool:
    """Returns whether input looks like two numeric coordinates, even if out of range."""
    return re.match(
        r"^\s*[-+]?\d+(?:\.\d+)?\s*[, ]\s*[-+]?\d+(?:\.\d+)?\s*$",
        query.strip(),
    ) is not None


def format_coordinates(lat: float, lon: float) -> str:
    """Formats latitude and longitude into human-readable cardinal degrees and raw floats."""
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.4f}° {lat_dir}, {abs(lon):.4f}° {lon_dir} ({lat:.4f}, {lon:.4f})"


def deduplicate_places(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicates places with identical names, states, countries, and near-identical GPS coords."""
    seen = set()
    unique = []
    for place in places:
        if not isinstance(place, dict):
            raise ValueError("Geocoding service returned an invalid location.")
        name = place.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Geocoding service returned a location without a name.")
        try:
            lat = float(place["lat"])
            lon = float(place["lon"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Geocoding service returned invalid coordinates.") from error
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Geocoding service returned coordinates out of range.")
        state = place.get("state") or ""
        country = place.get("country") or ""
        if not isinstance(state, str) or not isinstance(country, str):
            raise ValueError("Geocoding service returned invalid location details.")
        key = (
            name.strip().lower(),
            state.strip().lower(),
            country.strip().upper(),
            round(lat, 3),
            round(lon, 3),
        )
        if key not in seen:
            seen.add(key)
            unique.append(place)
    return unique


def get_places_by_name(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Finds all matching locations and their GPS coordinates using OpenWeather Geocoding API."""
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set in the environment.")

    url = "https://api.openweathermap.org/geo/1.0/direct"
    response = requests.get(
        url,
        params={"q": query, "limit": limit, "appid": api_key},
        timeout=10,
    )
    check_api_response(response, "Geocoding service")
    places = response.json()
    if not isinstance(places, list):
        raise ValueError("Geocoding service returned an invalid response.")
    return deduplicate_places(places)


def get_places_by_coordinates(lat: float, lon: float, limit: int = 5) -> List[Dict[str, Any]]:
    """Resolves GPS coordinates into place names using OpenWeather Reverse Geocoding API."""
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set in the environment.")

    url = "https://api.openweathermap.org/geo/1.0/reverse"
    response = requests.get(
        url,
        params={"lat": lat, "lon": lon, "limit": limit, "appid": api_key},
        timeout=10,
    )
    check_api_response(response, "Reverse geocoding service")
    places = response.json()
    if not isinstance(places, list):
        raise ValueError("Geocoding service returned an invalid response.")
    if places:
        return deduplicate_places(places)
    # If no named place found (e.g. open ocean/remote), return a synthetic entry
    return [{
        "name": "Custom GPS Location",
        "state": "",
        "country": "",
        "lat": lat,
        "lon": lon,
    }]


def get_weather_by_coordinates(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetches accurate weather data using exact GPS coordinates (latitude, longitude)."""
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set in the environment.")

    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=10,
    )
    check_api_response(response, "Weather service")
    weather = response.json()
    if not isinstance(weather, dict):
        raise ValueError("Weather service returned an invalid response.")
    return weather


def get_weather(city: str) -> Optional[Dict[str, Any]]:
    """Fallback: Fetches weather data by city name."""
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set in the environment.")

    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "appid": api_key, "units": "metric"},
        timeout=10,
    )
    check_api_response(response, "Weather service")
    return response.json()


def get_country_info(country_code: str) -> Optional[Dict[str, Any]]:
    """
    Fetches comprehensive country details from REST Countries API v5 using the 2-letter ISO code.
    """
    if not restcountries_api_key:
        raise RuntimeError("RESTCOUNTRIES_API_KEY is not set in the environment.")

    url = f"https://api.restcountries.com/countries/v5/codes.alpha_2/{country_code.upper()}"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {restcountries_api_key}"},
        params={
            "response_fields": (
                "names,codes,capitals,region,subregion,population,currencies,languages,timezones"
            )
        },
        timeout=10,
    )
    check_api_response(response, "Country service")
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Country service returned an invalid response.")
    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise ValueError("Country service returned an invalid response.")
    countries = data.get("objects", [])
    if not isinstance(countries, list):
        raise ValueError("Country service returned an invalid response.")
    return countries[0] if countries else None


def merge_travel_data(
    place: Dict[str, Any],
    weather_data: Dict[str, Any],
    country_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merges GPS location data, weather data, and country API information
    into a single unified data structure.
    """
    lat = float(place.get("lat", weather_data.get("coord", {}).get("lat", 0.0)))
    lon = float(place.get("lon", weather_data.get("coord", {}).get("lon", 0.0)))
    country_code = place.get("country") or weather_data.get("sys", {}).get("country", "")

    # Weather extraction
    main_weather = weather_data.get("main", {})
    weather_desc = weather_data.get("weather", [{}])[0]
    wind = weather_data.get("wind", {})

    weather_summary = {
        "temperature_c": main_weather.get("temp"),
        "feels_like_c": main_weather.get("feels_like"),
        "temp_min_c": main_weather.get("temp_min"),
        "temp_max_c": main_weather.get("temp_max"),
        "humidity_percent": main_weather.get("humidity"),
        "pressure_hpa": main_weather.get("pressure"),
        "condition": weather_desc.get("description", "").title(),
        "wind_speed_mps": wind.get("speed"),
    }

    # Country extraction
    country_summary: Dict[str, Any] = {}
    if country_data:
        capitals_list = country_data.get("capitals", [])
        capitals = ", ".join(c.get("name", "") for c in capitals_list if c.get("name"))
        currencies_list = country_data.get("currencies", [])
        currencies = ", ".join(
            f"{c.get('name', '')} ({c.get('code', '')})"
            for c in currencies_list
            if c.get("code")
        )
        languages_list = country_data.get("languages", [])
        languages = ", ".join(
            lang.get("name", "") for lang in languages_list if lang.get("name")
        )
        timezones_list = country_data.get("timezones", [])

        country_summary = {
            "common_name": country_data.get("names", {}).get("common", country_code),
            "official_name": country_data.get("names", {}).get("official", ""),
            "capital": capitals or "N/A",
            "region": country_data.get("region", "Unknown"),
            "subregion": country_data.get("subregion", ""),
            "population": country_data.get("population", 0),
            "currencies": currencies or "N/A",
            "languages": languages or "N/A",
            "timezones": timezones_list[:4] if timezones_list else [],
        }

    return {
        "location": {
            "name": place.get("name", weather_data.get("name", "Unknown")),
            "state": place.get("state", ""),
            "country_code": country_code,
            "latitude": lat,
            "longitude": lon,
            "gps_coordinates": format_coordinates(lat, lon),
        },
        "weather": weather_summary,
        "country": country_summary,
        "raw_data": {
            "geocoding_place": place,
            "weather": weather_data,
            "country": country_data,
        },
    }


def display_report(merged_data: Dict[str, Any]) -> None:
    """Displays a clean, informative report merging GPS, weather, and country data."""
    loc = merged_data["location"]
    weather = merged_data["weather"]
    country = merged_data.get("country", {})

    state_str = f", {loc['state']}" if loc.get("state") else ""
    country_code_str = f", {loc['country_code']}" if loc.get("country_code") else ""

    print("\n" + "=" * 60)
    print("           TRAVEL WEATHER & COUNTRY INTELLIGENCE")
    print("=" * 60)

    # 1. Location & GPS
    print("\n📍 LOCATION & GPS COORDINATES")
    print(f"   Place       : {loc['name']}{state_str}{country_code_str}")
    print(f"   GPS Coords  : {loc['gps_coordinates']}")

    # 2. Weather
    print("\n⛅ WEATHER OVERVIEW")
    temp = weather.get("temperature_c")
    feels_like = weather.get("feels_like_c")
    print(f"   Temperature : {temp}°C" + (f" (Feels like {feels_like}°C)" if feels_like is not None else ""))
    print(f"   Condition   : {weather.get('condition', 'N/A')}")
    print(f"   Humidity    : {weather.get('humidity_percent', 'N/A')}%")
    print(f"   Wind Speed  : {weather.get('wind_speed_mps', 'N/A')} m/s")
    if weather.get("pressure_hpa"):
        print(f"   Pressure    : {weather.get('pressure_hpa')} hPa")

    # 3. Country Information
    if country:
        print(f"\n🌍 COUNTRY PROFILE: {country.get('common_name', loc['country_code'])} ({loc['country_code']})")
        if country.get("official_name") and country.get("official_name") != country.get("common_name"):
            print(f"   Official    : {country.get('official_name')}")
        print(f"   Capital     : {country.get('capital', 'N/A')}")
        region_str = country.get("region", "Unknown")
        if country.get("subregion"):
            region_str += f" ({country.get('subregion')})"
        print(f"   Region      : {region_str}")
        print(f"   Population  : {country.get('population', 0):,}")
        print(f"   Currency    : {country.get('currencies', 'N/A')}")
        print(f"   Languages   : {country.get('languages', 'N/A')}")
        if country.get("timezones"):
            print(f"   Timezones   : {', '.join(country['timezones'])}")
    else:
        print("\n🌍 COUNTRY PROFILE")
        print("   No country profile available for this location.")

    print("\n" + "=" * 60)


def run_tool() -> Optional[Dict[str, Any]]:
    print("==================================================")
    print("           TRAVEL WEATHER & GPS TOOL              ")
    print("==================================================")
    print("Tip: Enter a city name (e.g. 'Paris', 'Nairobi')")
    print("     or exact GPS coordinates (e.g. '51.5074, -0.1278')\n")

    try:
        user_input = input("Enter a city name or GPS coordinates: ").strip()
    except EOFError:
        print("\nNo input available. Exiting.")
        return None
    except KeyboardInterrupt:
        print("\nCancelled.")
        return None

    if not user_input:
        print("No input entered. Exiting.")
        return None

    # Step 1: Detect if input is GPS coordinates or city name
    coords = parse_coordinates(user_input)
    if coords is None and is_coordinate_pair(user_input):
        print("Invalid coordinates. Latitude must be between -90 and 90, and longitude between -180 and 180.")
        return None

    try:
        if coords:
            lat, lon = coords
            print(f"\nLooking up GPS coordinates ({lat:.4f}, {lon:.4f}) via Reverse Geocoding...")
            places = get_places_by_coordinates(lat, lon)
        else:
            print(f"\nSearching GPS locations for '{user_input}'...")
            places = get_places_by_name(user_input, limit=5)
    except RuntimeError as error:
        print(f"Configuration error: {error}")
        return None
    except APIResponseError as error:
        print(error)
        return None
    except requests.exceptions.Timeout:
        print("The geocoding service timed out. Please try again.")
        return None
    except requests.exceptions.RequestException:
        print("Could not contact the geocoding service. Check your connection.")
        return None
    except ValueError as error:
        print(f"Invalid response from the geocoding service: {error}")
        return None

    if not places:
        print(f"No locations found for '{user_input}'. Please check the spelling or coordinates.")
        return None

    # Step 2: Show all places found in GPS and let user choose if multiple
    if len(places) == 1:
        selected_place = places[0]
        state_info = f", {selected_place['state']}" if selected_place.get("state") else ""
        print(f"\nFound location: {selected_place['name']}{state_info}, {selected_place.get('country', '')}")
        print(f"GPS: ({selected_place['lat']:.4f}, {selected_place['lon']:.4f})")
    else:
        print(f"\nFound {len(places)} matching GPS locations:")
        print("-" * 55)
        for idx, p in enumerate(places, 1):
            state_info = f", {p['state']}" if p.get("state") else ""
            c_code = f", {p['country']}" if p.get("country") else ""
            gps_str = f"GPS: ({p['lat']:.4f}, {p['lon']:.4f})"
            print(f"  [{idx}] {p['name']}{state_info}{c_code:<6} | {gps_str}")
        print("-" * 55)

        selection_prompt = f"Select a location [1-{len(places)}] (default 1): "
        try:
            choice = input(selection_prompt).strip()
            if not choice:
                selected_place = places[0]
            else:
                choice_idx = int(choice)
                if 1 <= choice_idx <= len(places):
                    selected_place = places[choice_idx - 1]
                else:
                    print(f"Invalid selection. Defaulting to [1] {places[0]['name']}.")
                    selected_place = places[0]
        except (ValueError, EOFError, KeyboardInterrupt):
            print(f"Defaulting to [1] {places[0]['name']}.")
            selected_place = places[0]

    if coords:
        selected_place = dict(selected_place, lat=coords[0], lon=coords[1])

    # Step 3: Fetch accurate weather using exact GPS coordinates
    lat = float(selected_place["lat"])
    lon = float(selected_place["lon"])
    print(f"\nFetching accurate weather for GPS coordinates ({lat:.4f}, {lon:.4f})...")

    try:
        weather_data = get_weather_by_coordinates(lat, lon)
    except RuntimeError as error:
        print(f"Configuration error: {error}")
        return None
    except APIResponseError as error:
        print(error)
        return None
    except requests.exceptions.Timeout:
        print("The weather service timed out. Please try again.")
        return None
    except requests.exceptions.RequestException:
        print("Could not contact the weather service. Check your connection.")
        return None
    except ValueError as error:
        print(f"Invalid response from the weather service: {error}")
        return None

    if not weather_data:
        print("Weather data could not be retrieved for this location.")
        return None

    # Step 4: Fetch Country data using Country Code
    country_code = selected_place.get("country") or weather_data.get("sys", {}).get("country")
    country_data = None
    if country_code:
        print(f"Merging country data for '{country_code}' from REST Countries API...")
        try:
            country_data = get_country_info(country_code)
        except (
            RuntimeError,
            APIResponseError,
            requests.exceptions.RequestException,
            ValueError,
        ):
            country_data = None

    # Step 5: Merge GPS Location + Weather + Country Data
    try:
        merged_data = merge_travel_data(selected_place, weather_data, country_data)
        display_report(merged_data)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        print(f"Could not build the travel report because API data was incomplete: {error}")
        return None

    # Step 6: Return the comprehensive report data for JSON export.
    return merged_data


def save_to_file(data: Dict[str, Any], filename: str) -> None:
    """Saves the merged travel dataset to a JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Full merged dataset successfully saved to '{filename}'.")
    except (OSError, TypeError, ValueError) as error:
        print(f"Could not save data to '{filename}': {error}")


if __name__ == "__main__":
    result = run_tool()
    if result:
        loc = result.get("location", {})
        place_name = loc.get("name", "location")
        c_code = loc.get("country_code", "")
        safe_name = re.sub(r"[^a-z0-9_-]+", "_", f"{place_name}_{c_code}".lower()).strip("_")
        filename = f"{safe_name or 'travel'}_weather_info.json"
        save_to_file(result, filename)
