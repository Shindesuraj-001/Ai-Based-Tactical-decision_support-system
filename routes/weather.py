"""
=============================================================
  routes/weather.py — Real-Time Weather Integration (NEW)
  Uses OpenWeatherMap free API to auto-detect weather
  conditions for the mission location and map them to
  the ATDSS weather categories (clear/fog/rain/night).

  Setup:
    1. Get free API key: https://openweathermap.org/api
    2. Set env var: export OPENWEATHER_API_KEY="your_key"
       OR edit app.py: app.config["OPENWEATHER_API_KEY"] = "key"
=============================================================
"""

import time
import requests
from flask import Blueprint, jsonify, request, current_app
from functools import wraps
from flask import session, redirect, url_for

weather_bp = Blueprint("weather", __name__)


# ─────────────────────────────────────────────
#  Map OpenWeatherMap condition codes → ATDSS categories
# ─────────────────────────────────────────────
def _map_weather_code(code, is_night=False):
    """
    Convert OWM weather code to one of:  clear | fog | rain | night
    Reference: https://openweathermap.org/weather-conditions
    """
    if is_night:
        return "night"
    if code == 800:                          # Clear sky
        return "clear"
    if 200 <= code < 600:                    # Thunderstorm / drizzle / rain
        return "rain"
    if 600 <= code < 700:                    # Snow → treat as fog/rain
        return "fog"
    if 700 <= code < 800:                    # Mist, fog, haze, dust, smoke
        return "fog"
    if 801 <= code <= 804:                   # Cloudy → treat as clear (overcast still visible)
        return "clear"
    return "clear"


def _describe_impact(weather_type):
    """Return a short tactical impact note for this weather."""
    return {
        "clear": "Clear skies allow full visibility. Enemy can detect movement easily.",
        "fog":   "Fog provides stealth advantage. Reduces enemy spotting range by ~60%.",
        "rain":  "Rain suppresses sound — ideal for silent approach. Mud may slow vehicles.",
        "night": "Night conditions favour forces with NVG equipment. Stealth premium.",
    }.get(weather_type, "Standard conditions.")


# ─────────────────────────────────────────────
#  WEATHER API ENDPOINT
# ─────────────────────────────────────────────
@weather_bp.route("/api/weather")
def get_weather():
    """
    GET /api/weather?lat=28.6139&lng=77.2090
    Returns real weather data mapped to ATDSS categories.
    Falls back to mock data if no API key is configured.
    """
    lat = request.args.get("lat", 28.6139, type=float)
    lng = request.args.get("lng", 77.2090, type=float)
    api_key = current_app.config.get("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")

    # ── No API key → return mock data ─────────
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        import random
        mock_type = random.choice(["clear", "fog", "rain", "night"])
        return jsonify({
            "status":          "mock",
            "weather_type":    mock_type,
            "description":     f"{mock_type.title()} (demo mode — add API key for live data)",
            "temperature":     round(random.uniform(15, 38), 1),
            "humidity":        random.randint(30, 90),
            "wind_speed":      round(random.uniform(5, 45), 1),
            "city":            "Location (Demo)",
            "tactical_impact": _describe_impact(mock_type),
            "icon":            "01d",
        })

    # ── Fetch live data from OpenWeatherMap ───
    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lng, "appid": api_key, "units": "metric"},
            timeout=6
        )
        resp.raise_for_status()
        d = resp.json()

        code     = d["weather"][0]["id"]
        now      = time.time()
        sunrise  = d["sys"]["sunrise"]
        sunset   = d["sys"]["sunset"]
        is_night = not (sunrise < now < sunset)

        weather_type = _map_weather_code(code, is_night)

        return jsonify({
            "status":          "success",
            "weather_type":    weather_type,
            "description":     d["weather"][0]["description"].title(),
            "temperature":     round(d["main"]["temp"], 1),
            "humidity":        d["main"]["humidity"],
            "wind_speed":      round(d["wind"].get("speed", 0) * 3.6, 1),  # m/s → km/h
            "city":            d.get("name", "Unknown Location"),
            "tactical_impact": _describe_impact(weather_type),
            "icon":            d["weather"][0].get("icon", "01d"),
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "status":          "error",
            "message":         "Cannot connect to weather service. Check internet connection.",
            "weather_type":    "clear",
            "tactical_impact": _describe_impact("clear"),
        }), 503

    except Exception as e:
        return jsonify({
            "status":          "error",
            "message":         str(e),
            "weather_type":    "clear",
            "tactical_impact": _describe_impact("clear"),
        }), 500