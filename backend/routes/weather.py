"""
weather.py — Weather data from Open-Meteo free API with farming advisory.
"""
from fastapi import APIRouter, Query
import httpx

router = APIRouter()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Coordinates for known mandis
MANDI_COORDS = {
    "Nashik":     {"lat": 20.0059, "lon": 73.7898},
    "Lasalgaon":  {"lat": 20.1895, "lon": 74.2276},
    "Pune":       {"lat": 18.5204, "lon": 73.8567},
    "Kolhapur":   {"lat": 16.7050, "lon": 74.2433},
    "Mumbai":     {"lat": 19.0760, "lon": 72.8777},
    "Delhi":      {"lat": 28.6139, "lon": 77.2090},
    "Nagpur":     {"lat": 21.1458, "lon": 79.0882},
    "Aurangabad": {"lat": 19.8762, "lon": 75.3433},
}


def get_weather_description(code: int) -> str:
    """Map WMO weather code to human-readable description."""
    descriptions = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
        3: "Overcast", 45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Freezing drizzle (light)", 57: "Freezing drizzle (dense)",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Freezing rain (light)", 67: "Freezing rain (heavy)",
        71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
        77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
        82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return descriptions.get(code, "Unknown")


@router.get("/weather")
async def get_weather(
    mandi: str = Query("Nashik", description="Mandi/market name"),
):
    """Fetch 7-day weather forecast from Open-Meteo with farming advisory."""
    coords = MANDI_COORDS.get(mandi, MANDI_COORDS["Nashik"])

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": 7,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract current weather
        current = data.get("current", {})
        daily = data.get("daily", {})

        # Calculate farming advisory based on next 3 days precipitation
        precip_sums = daily.get("precipitation_sum", [])
        next_3_days_precip = sum(precip_sums[:3]) if len(precip_sums) >= 3 else sum(precip_sums)

        if next_3_days_precip > 10:
            farming_advisory = "🌧️ Heavy rainfall expected in the next 3 days. Consider delaying harvest and protect stored crops from moisture."
        elif next_3_days_precip < 2:
            farming_advisory = "☀️ Dry conditions expected. Ensure adequate irrigation for your crops and conserve water resources."
        else:
            farming_advisory = "🌤️ Moderate weather conditions. Suitable for regular farming activities and fieldwork."

        # Build 7-day forecast array
        daily_forecast = []
        if daily.get("time"):
            for i, date in enumerate(daily["time"]):
                daily_forecast.append({
                    "date": date,
                    "temp_max": daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                    "temp_min": daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                    "precipitation_sum": daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                })

        return {
            "mandi": mandi,
            "coordinates": coords,
            "current": {
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "precipitation": current.get("precipitation"),
                "weather_code": current.get("weather_code"),
                "weather_description": get_weather_description(current.get("weather_code", 0)),
            },
            "daily_forecast": daily_forecast,
            "farming_advisory": farming_advisory,
            "next_3_days_precipitation_mm": round(next_3_days_precip, 1),
        }

    except Exception as e:
        print(f"[weather] Open-Meteo fetch error: {e}")
        return {
            "mandi": mandi,
            "error": f"Weather data unavailable: {str(e)}",
            "farming_advisory": "Weather data could not be fetched. Please try again later.",
        }
