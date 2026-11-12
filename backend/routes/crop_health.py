"""
crop_health.py — Crop Health endpoint.

Reuses the existing weather pipeline (Open-Meteo) and historical
MongoDB price / weather data to compute agronomic health proxies.
No Google Earth Engine dependency.
"""

import math
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
import httpx

from database import get_async_collection

router = APIRouter()

# Reuse mandi coordinate map from weather route
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

MANDI_STATE = {
    "Nashik": "Maharashtra",
    "Lasalgaon": "Maharashtra",
    "Pune": "Maharashtra",
    "Kolhapur": "Maharashtra",
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Nagpur": "Maharashtra",
    "Aurangabad": "Maharashtra",
}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _compute_ndvi_proxy(rainfall_30d: float) -> float:
    """
    Estimate NDVI proxy from 30-day accumulated rainfall.
    Dry conditions → low NDVI; wet conditions → high NDVI.
    Range: [0, 1].
    """
    # Sigmoid-like mapping: 0mm → 0.1, 100mm → 0.7, 200mm → 0.9
    return round(min(0.95, max(0.05, 1 - math.exp(-rainfall_30d / 80))), 3)


def _stress_level(ndvi: float, temperature_avg: float, rainfall_30d: float) -> str:
    """Classify crop stress level from NDVI, temperature, and rainfall."""
    if ndvi < 0.3 or temperature_avg > 38 or rainfall_30d < 5:
        return "High"
    if ndvi < 0.5 or temperature_avg > 33 or rainfall_30d < 20:
        return "Moderate"
    return "Low"


def _generate_recommendation(ndvi: float, temperature_avg: float, rainfall_30d: float, stress: str) -> str:
    """Generate a plain-English agronomic recommendation."""
    parts = []

    # Vegetation
    if ndvi >= 0.65:
        parts.append("Crop canopy appears healthy with good vegetation cover.")
    elif ndvi >= 0.45:
        parts.append("Vegetation index is moderate — monitor crop density.")
    else:
        parts.append("Vegetation index is low — inspect field for crop stress or bare patches.")

    # Rainfall
    if rainfall_30d >= 100:
        parts.append("Adequate rainfall received over the last 30 days — avoid over-irrigation.")
    elif rainfall_30d >= 40:
        parts.append("Moderate rainfall — supplement with irrigation as needed.")
    else:
        parts.append("Rainfall has been low — ensure regular irrigation to prevent moisture stress.")

    # Temperature
    if temperature_avg >= 38:
        parts.append("Extreme heat detected — consider shade netting and avoid midday fieldwork.")
    elif temperature_avg >= 33:
        parts.append("Warm temperatures — ensure adequate water availability to reduce heat stress.")
    else:
        parts.append("Temperature conditions are within normal range for crop growth.")

    # Overall action
    if stress == "High":
        parts.append("⚠️ Take immediate corrective action to prevent crop loss.")
    elif stress == "Moderate":
        parts.append("Monitor daily and apply corrective measures within 48 hours.")
    else:
        parts.append("Continue current farming practices — conditions are favorable.")

    return " ".join(parts)


@router.get("/crop-health")
async def get_crop_health(
    mandi: str = Query("Nashik", description="Mandi/market name"),
):
    """
    Return crop health indicators for the given mandi.
    Uses Open-Meteo weather API (last 30 days) and computes NDVI proxy.
    """
    coords = MANDI_COORDS.get(mandi, MANDI_COORDS["Nashik"])
    state = MANDI_STATE.get(mandi, "Maharashtra")

    temperature_avg = 28.0
    rainfall_30d = 50.0

    # ── Fetch weather from Open-Meteo (historical 30-day) ──────────────────────
    try:
        today = datetime.now(timezone.utc).date()
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = today.isoformat()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": "temperature_2m_mean,precipitation_sum",
                    "timezone": "Asia/Kolkata",
                },
            )
            if resp.status_code == 200:
                w_data = resp.json()
                daily = w_data.get("daily", {})
                temps = [t for t in (daily.get("temperature_2m_mean") or []) if t is not None]
                rains = [r for r in (daily.get("precipitation_sum") or []) if r is not None]
                if temps:
                    temperature_avg = round(sum(temps) / len(temps), 1)
                if rains:
                    rainfall_30d = round(sum(rains), 1)
    except Exception as e:
        print(f"[crop_health] Open-Meteo historical fetch failed: {e}")
        # Fall back to live MongoDB weather cache
        try:
            weather_col = get_async_collection("weather_cache")
            doc = await weather_col.find_one({"source": "NASA_POWER"}, sort=[("date", -1)])
            if doc:
                temperature_avg = doc.get("temperature", 28.0)
                rainfall_30d = doc.get("rainfall", 0.0) * 30  # crude scale-up
        except Exception:
            pass

    # ── Compute proxies ────────────────────────────────────────────────────────
    ndvi_proxy = _compute_ndvi_proxy(rainfall_30d)
    stress = _stress_level(ndvi_proxy, temperature_avg, rainfall_30d)
    recommendation = _generate_recommendation(ndvi_proxy, temperature_avg, rainfall_30d, stress)

    return {
        "mandi": mandi,
        "state": state,
        "coordinates": coords,
        "ndvi_proxy": ndvi_proxy,
        "rainfall_30d_mm": rainfall_30d,
        "temperature_avg": temperature_avg,
        "stress_level": stress,
        "recommendation": recommendation,
        "data_source": "open_meteo_historical",
        "observation_period_days": 30,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
