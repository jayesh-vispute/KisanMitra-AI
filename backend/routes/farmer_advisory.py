"""
farmer_advisory.py — Farmer Advisory endpoint.

Generates structured, plain-language advisories based on:
- Current market price (from MongoDB market_prices collection)
- Weather conditions (from Open-Meteo)
- Simple price trend (from price_history MongoDB cache)
- Commodity & mandi context

Returns all fields consumed by FarmerAdvisory.jsx:
  advisory_text, advisory_text_hi, best_sell_window,
  expected_price_range, trend, weather_summary, commodity, mandi
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Query
import httpx

from database import get_async_collection

router = APIRouter()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

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


async def _get_current_price(commodity: str, market: str) -> Optional[float]:
    """Fetch the latest modal price from MongoDB market_prices collection."""
    try:
        col = get_async_collection("market_prices")
        query = {"commodity": {"$regex": f"^{commodity.strip()}$", "$options": "i"}}
        if market:
            query["market"] = {"$regex": f"^{market.strip()}$", "$options": "i"}
        doc = await col.find_one(query, sort=[("date", -1)])
        if doc:
            return float(doc.get("modal_price") or doc.get("price") or 0)
    except Exception as e:
        print(f"[farmer_advisory] Failed to get current price: {e}")
    return None


async def _get_price_trend(commodity: str, market: str) -> float:
    """Compute 7-day trend percentage from price_history MongoDB cache."""
    try:
        col = get_async_collection("price_history")
        cache_key = f"{commodity}_{market}".lower().strip()
        doc = await col.find_one({"cache_key": cache_key})
        if doc and doc.get("records"):
            records = doc["records"]
            # Parse and sort by date
            parsed = []
            for r in records:
                try:
                    from datetime import datetime as dt
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                        try:
                            d = dt.strptime(r.get("arrival_date", ""), fmt)
                            p = float(r.get("modal_price", 0))
                            if p > 0:
                                parsed.append((d, p))
                            break
                        except (ValueError, AttributeError):
                            continue
                except Exception:
                    continue
            parsed.sort(key=lambda x: x[0])
            if len(parsed) >= 7:
                current = parsed[-1][1]
                week_ago = parsed[-7][1]
                if week_ago > 0:
                    return round(((current - week_ago) / week_ago) * 100, 2)
    except Exception as e:
        print(f"[farmer_advisory] Failed to get price trend: {e}")
    return 0.0


async def _get_weather_summary(mandi: str) -> dict:
    """Fetch current weather for the mandi from Open-Meteo."""
    coords = MANDI_COORDS.get(mandi, MANDI_COORDS["Nashik"])
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "current": "temperature_2m,precipitation,weather_code",
                    "daily": "precipitation_sum",
                    "forecast_days": 3,
                    "timezone": "Asia/Kolkata",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                temp = current.get("temperature_2m", 28.0)
                precip = current.get("precipitation", 0.0)
                daily = data.get("daily", {})
                next3 = sum(daily.get("precipitation_sum", [])[:3])
                return {
                    "temperature": temp,
                    "precipitation": precip,
                    "next_3d_rain_mm": round(next3, 1),
                }
    except Exception as e:
        print(f"[farmer_advisory] Weather fetch failed: {e}")
    return {"temperature": 28.0, "precipitation": 0.0, "next_3d_rain_mm": 0.0}


def _generate_advisory(
    commodity: str,
    mandi: str,
    current_price: float,
    trend: float,
    weather: dict,
) -> tuple[str, str]:
    """
    Generate advisory text in English and Hindi.
    Returns (advisory_en, advisory_hi).
    """
    temp = weather.get("temperature", 28.0)
    rain_3d = weather.get("next_3d_rain_mm", 0.0)
    price_str = f"₹{int(current_price):,}/qtl" if current_price else "N/A"

    # Price direction
    if trend > 3:
        price_signal = "rising significantly"
        action_en = "Consider holding your produce for 3–5 days to benefit from the upward trend."
        action_hi = "अगले 3-5 दिन रुकें — कीमत और बढ़ सकती है।"
        window = "Next 3–5 days"
    elif trend > 0:
        price_signal = "slightly rising"
        action_en = "Prices are slightly up. You may sell now or wait 1–2 days for a better rate."
        action_hi = "कीमत थोड़ी बढ़ रही है। अभी बेचें या 1-2 दिन प्रतीक्षा करें।"
        window = "Today or tomorrow"
    elif trend < -3:
        price_signal = "falling significantly"
        action_en = "Prices are falling. Consider selling soon to avoid further losses."
        action_hi = "कीमत गिर रही है। जल्दी बेचना फायदेमंद होगा।"
        window = "Sell immediately"
    elif trend < 0:
        price_signal = "slightly falling"
        action_en = "Prices are marginally lower. Selling today is advisable."
        action_hi = "कीमत थोड़ी कम है। आज बेचना बेहतर रहेगा।"
        window = "Today"
    else:
        price_signal = "stable"
        action_en = "Prices are stable. You can sell now at the current market rate."
        action_hi = "कीमत स्थिर है। आप अभी बाजार भाव पर बेच सकते हैं।"
        window = "Flexible"

    # Weather context
    if rain_3d > 15:
        weather_note_en = "Heavy rain is expected in the next 3 days — protect stored crops from moisture and delay transport if possible."
        weather_note_hi = "अगले 3 दिनों में भारी बारिश की संभावना है — फसल को नमी से बचाएं।"
    elif rain_3d > 5:
        weather_note_en = "Light rainfall is expected. Monitor your stored produce for moisture."
        weather_note_hi = "हल्की बारिश की संभावना है। भंडारित फसल की नमी की जाँच करें।"
    elif temp > 36:
        weather_note_en = "High heat today. Ensure your crop storage is ventilated to prevent spoilage."
        weather_note_hi = "आज बहुत गर्मी है। भंडारण में हवा का प्रबंध करें।"
    else:
        weather_note_en = "Weather conditions are normal. No special precautions needed."
        weather_note_hi = "मौसम सामान्य है। कोई विशेष सावधानी आवश्यक नहीं।"

    advisory_en = (
        f"Current {commodity} price in {mandi} is {price_str} — prices are {price_signal} "
        f"({'+' if trend >= 0 else ''}{trend:.1f}% this week). "
        f"{action_en} {weather_note_en}"
    )
    advisory_hi = (
        f"{mandi} में {commodity} का वर्तमान भाव {price_str} है। कीमत "
        f"{'बढ़' if trend >= 0 else 'घट'}ी है ({'+' if trend >= 0 else ''}{trend:.1f}% इस सप्ताह)। "
        f"{action_hi} {weather_note_hi}"
    )
    return advisory_en, advisory_hi


def _expected_price_range(current_price: float, trend: float) -> str:
    """Estimate a 7-day expected price range string."""
    if not current_price or current_price <= 0:
        return "N/A"
    low = int(current_price * (1 + (trend - 5) / 100))
    high = int(current_price * (1 + (trend + 5) / 100))
    low = max(0, low)
    high = max(low, high)
    return f"{low:,}–{high:,}"


@router.get("/farmer-advisory")
async def get_farmer_advisory(
    commodity: str = Query("Onion", description="Commodity name"),
    mandi: str = Query("Nashik", description="Market/Mandi name"),
):
    """
    Generate a structured farmer advisory for the given commodity and mandi.
    Uses current market price, weather data, and price trend from MongoDB.
    """
    # Fetch all required data concurrently-ish
    current_price = await _get_current_price(commodity, mandi)
    trend = await _get_price_trend(commodity, mandi)
    weather = await _get_weather_summary(mandi)

    # If no live price found, use a reasonable proxy from price_history
    if not current_price or current_price == 0:
        try:
            col = get_async_collection("price_history")
            cache_key = f"{commodity}_{mandi}".lower().strip()
            doc = await col.find_one({"cache_key": cache_key})
            if doc and doc.get("records"):
                last = doc["records"][-1]
                current_price = float(last.get("modal_price", 0) or last.get("price", 0))
        except Exception:
            pass
        if not current_price:
            current_price = 2000.0  # generic proxy

    advisory_en, advisory_hi = _generate_advisory(commodity, mandi, current_price, trend, weather)

    return {
        "commodity": commodity,
        "mandi": mandi,
        "current_price": round(current_price, 2),
        "trend_percent": trend,
        "advisory_text": advisory_en,
        "advisory_text_hi": advisory_hi,
        "best_sell_window": _expected_price_range(current_price, trend),  # price range used as window proxy
        "expected_price_range": _expected_price_range(current_price, trend),
        "weather_summary": {
            "temperature_c": weather.get("temperature"),
            "next_3d_rain_mm": weather.get("next_3d_rain_mm"),
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
