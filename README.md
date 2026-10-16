Here is the complete `README.md` for your **Travel Weather & GPS Intelligence Tool**, organized precisely in your requested order:

---

# Travel Weather & GPS Intelligence Tool

A Python application that combines OpenWeather geocoding and live weather data with demographic and geographic insights from the REST Countries API. It allows you to search for any city by name or exact GPS coordinates to generate a comprehensive travel weather intelligence report and export the results to JSON.

---

## Features

* **Dual-Mode Lookup:** Search locations using city names (with support for multiple matching places and selection) or exact GPS coordinates (latitude and longitude).
* **Precise Weather Intelligence:** Fetches real-time weather metrics using exact coordinates via the OpenWeather API, including temperature, "feels like" temperature, humidity, wind speed, pressure, and descriptions.
* **Country Enrichment:** Automatically queries the REST Countries API using ISO country codes to pull official names, capitals, regions, population statistics, currencies, languages, and timezones.
* **Data Merging & Export:** Consolidates location, weather, and country data into a unified structure and exports the complete dataset to a structured JSON file.
* **Robust Error Handling:** Includes UTF-8 console support across platforms, environment configuration checks via `python-dotenv`, coordinate validation, and request timeout handling.

---

## Project Structure

```text
travel-weather-tool/
│
├── day3_travel_info.py      # Main application script
├── .env.example             # Environment variable template (no secrets)
├── .env                     # Local API keys (ignored by Git)
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation

```

## Setup

1. Install the dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and add your API keys.
3. Run the application with `python day3_travel_info.py`.

Generated `*_weather_info.json` reports are kept locally and ignored by Git.

---

## System Flow

1. **Input & Parsing**: The user provides either a city name or latitude/longitude coordinates. The input is validated using regular expressions.
2. **Geocoding / Resolution**:
* If a name is given, the **OpenWeather Direct Geocoding API** fetches matching locations (with deduplication). If multiple matches occur, the user is prompted to select one.
* If GPS coordinates are given, the **OpenWeather Reverse Geocoding API** resolves them into a readable location name.


3. **Weather Retrieval**: Exact latitude and longitude coordinates are sent to the **OpenWeather Weather API** using metric units (`units=metric`).
4. **Country Profile Enrichment**: Using the ISO country code obtained from the location data, the **REST Countries API** is queried for demographics, capital cities, languages, currencies, and timezones.
5. **Merging & Output**: All responses are merged into a unified dictionary structure, displayed cleanly in the terminal with structured sections, and automatically exported to a `.json` file.

---

## Architecture

The application follows a linear, modular architecture designed to decouple location resolution, weather retrieval, demographic enrichment, and reporting.

```text
 [ User Input ] (City Name or GPS Coords)
       │
       ▼
 [ Coordinate Parser ] ──(If GPS)──► [ Reverse Geocoding API ]
       │                                     │
    (If Name)                                │
       ▼                                     ▼
 [ Direct Geocoding API ] ──────────► [ Place Selection / Deduplication ]
                                             │
                                             ▼
                                    [ OpenWeather API ]
                                    (Fetch Live Weather)
                                             │
                                             ▼
                                  [ REST Countries API ]
                                  (Fetch Country Profile)
                                             │
                                             ▼
                                  [ Data Merging Engine ]
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
             [ Terminal Report ]                           [ JSON Export File ]

```

---

## Example Output

### Terminal Display Report

```text
==================================================
           TRAVEL WEATHER & COUNTRY INTELLIGENCE
==================================================

📍 LOCATION & GPS COORDINATES
   Place       : Nairobi, Nairobi Area, KE
   GPS Coords  : 1.2864° S, 36.8172° E (-1.2864, 36.8172)

⛅ WEATHER OVERVIEW
   Temperature : 24.5°C (Feels like 24.1°C)
   Condition   : Few Clouds
   Humidity    : 48%
   Wind Speed  : 3.6 m/s
   Pressure    : 1014 hPa

🌍 COUNTRY PROFILE: Kenya (KE)
   Official    : Republic of Kenya
   Capital     : Nairobi
   Region      : Africa (Eastern Africa)
   Population  : 55,339,000
   Currency    : Kenyan shilling (KES)
   Languages   : English, Swahili
   Timezones   : UTC+03:00

==================================================
Full merged dataset successfully saved to 'nairobi_ke_weather_info.json'.

```

### Generated JSON Output (`nairobi_ke_weather_info.json`)

```json
{
  "location": {
    "name": "Nairobi",
    "state": "Nairobi Area",
    "country_code": "KE",
    "latitude": -1.2864,
    "longitude": 36.8172,
    "gps_coordinates": "1.2864° S, 36.8172° E (-1.2864, 36.8172)"
  },
  "weather": {
    "temperature_c": 24.5,
    "feels_like_c": 24.1,
    "temp_min_c": 23.0,
    "temp_max_c": 26.0,
    "humidity_percent": 48,
    "pressure_hpa": 1014,
    "condition": "Few Clouds",
    "wind_speed_mps": 3.6
  },
  "country": {
    "common_name": "Kenya",
    "official_name": "Republic of Kenya",
    "capital": "Nairobi",
    "region": "Africa",
    "subregion": "Eastern Africa",
    "population": 55339000,
    "currencies": "Kenyan shilling (KES)",
    "languages": "English, Swahili",
    "timezones": ["UTC+03:00"]
  }
}

```

---

## Technologies Used & Learning Focus

### Technologies Used

* **Python 3.8+**: Core programming language.
* **Requests Library**: For handling HTTP GET requests to external REST APIs.
* **Python-Dotenv**: For secure environment variable and API key management.
* **OpenWeather Geocoding & Weather APIs**: For direct coordinate lookup, reverse geocoding, and real-time weather metrics.
* **REST Countries API v5**: For retrieving official country names, regions, populations, currencies, languages, and timezones.

### Learning Focus

* **API Integration & Chaining**: Combining multiple independent third-party APIs (geocoding, weather, and demographics) sequentially into a single unified pipeline.
* **Robust Error Handling**: Managing network timeouts, missing environment configurations, HTTP status codes (`404`, `400`), and data normalization.
* **Data Structuring & Serialization**: Merging disparate JSON payloads into a clean, standardized data dictionary and exporting it cleanly with UTF-8 encoding.

---

## Author

**Branham Simiyu**