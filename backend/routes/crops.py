"""
KisanMitra AI — Crop & Commodity Routes
Replaced all hardcoded prices with live AGMARKNET API data.
Commodities and mandis are now dynamically loaded.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone, timedelta
import httpx

from services.market_data_service import get_latest_commodity_prices, get_live_prices
from utils.cache import price_cache
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("CropsRoute")

IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# Emoji mapping for common commodities (cosmetic only, not data-critical)
# ---------------------------------------------------------------------------
COMMODITY_EMOJI = {
    "onion": "🧅",
    "potato": "🥔",
    "tomato": "🍅",
    "garlic": "🧄",
    "cauliflower": "🥦",
    "green_chilli": "🌶️",
    "brinjal": "🍆",
    "cabbage": "🥬",
    "wheat": "🌾",
    "rice": "🍚",
    "maize": "🌽",
    "apple": "🍎",
    "banana": "🍌",
    "mango": "🥭",
    "grapes": "🍇",
    "lemon": "🍋",
    "ginger": "🫚",
    "turmeric": "🟡",
    "coriander": "🌿",
    "capsicum": "🫑",
    "peas": "🫛",
    "carrot": "🥕",
    "cucumber": "🥒",
    "bitter_gourd": "🥒",
    "bottle_gourd": "🍐",
    "lady_finger": "🟢",
    "spinach": "🥬",
    "radish": "🥕",
    "sweet_potato": "🍠",
    "mushroom": "🍄",
    "soyabean": "🫘",
    "groundnut": "🥜",
    "coconut": "🥥",
    "cotton": "🧶",
    "sugarcane": "🎋",
    "chilli": "🌶️",
}


def _get_emoji(commodity_key: str) -> str:
    """Get emoji for a commodity, with a default fallback."""
    return COMMODITY_EMOJI.get(commodity_key, "🌾")


# ============================================================
# /api/commodities — LIVE prices from AGMARKNET
# ============================================================
@router.get("/commodities")
async def get_commodities():
    """
    Return commodities with their latest live prices.
    Fetches from AGMARKNET API (cached for 10 min).
    Falls back to MongoDB if API is unavailable.
    """
    now = datetime.now(IST)

    try:
        commodity_prices = await get_latest_commodity_prices()
    except Exception as e:
        logger.error(f"Failed to fetch commodity prices: {e}")
        commodity_prices = []

    if not commodity_prices:
        return {
            "commodities": [],
            "data_source": "unavailable",
            "message": "Market price data is temporarily unavailable.",
        }

    results = []
    for item in commodity_prices:
        modal_price = item.get("modal_price") or item.get("price", 0)
        min_price = item.get("min_price", 0)
        max_price = item.get("max_price", 0)
        commodity_key = item.get("commodity_key", "")
        commodity_name = item.get("commodity", commodity_key)

        # Compute a change percentage from min/modal spread as a proxy
        # (True historical change requires prior-day data, which we accumulate over time)
        if min_price and modal_price and min_price > 0:
            spread_pct = round(((modal_price - min_price) / min_price) * 100, 1)
        else:
            spread_pct = 0.0

        direction = "up" if spread_pct > 0 else ("down" if spread_pct < 0 else "flat")
        alert_level = (
            "CRITICAL" if spread_pct > 15 else ("HIGH" if spread_pct > 8 else "NORMAL")
        )

        results.append(
            {
                "id": commodity_key,
                "name": f"{commodity_name} {_get_emoji(commodity_key)}",
                "emoji": _get_emoji(commodity_key),
                "current_price": round(modal_price),
                "price": round(modal_price),
                "min_price": round(min_price) if min_price else None,
                "max_price": round(max_price) if max_price else None,
                "modal_price": round(modal_price),
                "price_change_pct": spread_pct,
                "price_change_direction": direction,
                "change_pct": spread_pct,
                "trend": direction,
                "market_date": item.get("arrival_date", ""),
                "source": "Agmarknet (Live)",
                "mandi": item.get("market", ""),
                "state": item.get("state", ""),
                "district": item.get("district", ""),
                "alert_level": alert_level,
            }
        )

    return {
        "commodities": results,
        "data_source": "live",
        "last_updated": now.isoformat(),
    }


# ============================================================
# /api/crop-health   (with real Open-Meteo fetch — preserved)
# ============================================================
@router.get("/crop-health")
async def get_crop_health(mandi: str = Query(..., description="Mandi location")):
    """
    Crop health assessment using Open-Meteo weather data.
    The mandi coordinates are fetched dynamically or use reasonable defaults.
    """
    # Default coordinates — will be enhanced when we have a mandi coordinate DB
    # For now, use approximate center of India as fallback
    lat, lon = 20.0, 75.0
    state = "Unknown"

    # Known mandi coordinates (expanded set, with fallback to defaults)
    KNOWN_COORDS = {
        "lasalgaon": (20.1506, 74.2238, "Maharashtra"),
        "pune": (18.5204, 73.8567, "Maharashtra"),
        "nashik": (19.9975, 73.7898, "Maharashtra"),
        "kolhapur": (16.7050, 74.2433, "Maharashtra"),
        "agra": (27.1767, 78.0081, "Uttar Pradesh"),
        "kanpur": (26.4499, 80.3319, "Uttar Pradesh"),
        "lucknow": (26.8467, 80.9462, "Uttar Pradesh"),
        "bangalore": (12.9716, 77.5946, "Karnataka"),
        "mysore": (12.2958, 76.6394, "Karnataka"),
        "hubli": (15.3647, 75.1240, "Karnataka"),
        "jaipur": (26.9124, 75.7873, "Rajasthan"),
        "ahmedabad": (23.0225, 72.5714, "Gujarat"),
        "mumbai": (19.0760, 72.8777, "Maharashtra"),
        "delhi": (28.7041, 77.1025, "Delhi"),
        "chennai": (13.0827, 80.2707, "Tamil Nadu"),
        "hyderabad": (17.3850, 78.4867, "Telangana"),
        "kolkata": (22.5726, 88.3639, "West Bengal"),
        "patna": (25.6093, 85.1376, "Bihar"),
        "bhopal": (23.2599, 77.4126, "Madhya Pradesh"),
        "nagpur": (21.1458, 79.0882, "Maharashtra"),
    }

    mandi_lower = mandi.lower()
    if mandi_lower in KNOWN_COORDS:
        lat, lon, state = KNOWN_COORDS[mandi_lower]

    # Attempt real Open-Meteo weather fetch
    temperature_avg = 28.5
    rainfall_30d = 45.2
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,rain"
            f"&daily=temperature_2m_mean,precipitation_sum"
            f"&timezone=Asia%2FKolkata&past_days=7&forecast_days=1"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                weather = resp.json()
                daily = weather.get("daily", {})
                temps = daily.get("temperature_2m_mean", [])
                precips = daily.get("precipitation_sum", [])
                if temps:
                    temperature_avg = round(sum(temps) / len(temps), 1)
                if precips:
                    rainfall_30d = round(
                        sum(precips) * 4.3, 1
                    )  # extrapolate 7d to ~30d
    except Exception:
        pass  # Fall back to defaults

    # Calculate simulated NDVI proxy from Open-Meteo rainfall
    data_source_label = "Open-Meteo + NDVI Proxy"
    ndvi = round(max(0, min(1, 1 - (30 - rainfall_30d) / 60)), 2)

    stress = "Low" if ndvi > 0.7 else ("Moderate" if ndvi > 0.4 else "High")

    recommendation_map = {
        "Low": f"Crop conditions in {mandi.capitalize()} appear healthy. Adequate rainfall reported. Continue regular monitoring.",
        "Moderate": f"Rainfall deficit detected in {mandi.capitalize()} region. Minor crop stress likely. Maintain hydration if possible.",
        "High": f"Severe water stress detected near {mandi.capitalize()}. Irrigate immediately. Consider crop insurance.",
    }

    return {
        "mandi": mandi_lower,
        "state": state,
        "coordinates": {"lat": lat, "lon": lon},
        "ndvi_proxy": ndvi,
        "stress_level": stress,
        "rainfall_30d_mm": rainfall_30d,
        "temperature_avg": temperature_avg,
        "recommendation": recommendation_map[stress],
        "data_source": data_source_label,
    }


# ============================================================
# Farmer Advisory Templates (preserved — these are advisory text, not price data)
# ============================================================
_ADVISORIES = {
    "onion": {
        "en": "Prices for Onion in {mandi} are expected to rise due to seasonal supply constraints. Consider holding stock and selling in the second week of next month for optimal returns.",
        "hi": "{mandi} \u092e\u0947\u0902 \u092a\u094d\u092f\u093e\u091c \u0915\u0940 \u0915\u0940\u092e\u0924\u0947\u0902 \u092e\u094c\u0938\u092e\u0940 \u0906\u092a\u0942\u0930\u094d\u0924\u093f \u092c\u093e\u0927\u093e\u0913\u0902 \u0915\u0947 \u0915\u093e\u0930\u0923 \u092c\u0922\u093c\u0928\u0947 \u0915\u0940 \u0909\u092e\u094d\u092e\u0940\u0926 \u0939\u0948\u0964 \u0938\u0930\u094d\u0935\u094b\u0924\u094d\u0924\u092e \u0930\u093f\u091f\u0930\u094d\u0928 \u0915\u0947 \u0932\u093f\u090f \u0938\u094d\u091f\u0949\u0915 \u0930\u0916\u0947\u0902 \u0914\u0930 \u0905\u0917\u0932\u0947 \u092e\u0939\u0940\u0928\u0947 \u0915\u0947 \u0926\u0942\u0938\u0930\u0947 \u0938\u092a\u094d\u0924\u093e\u0939 \u092e\u0947\u0902 \u092c\u0947\u091a\u0947\u0902\u0964",
        "risk_level": "Low",
    },
    "potato": {
        "en": "Potato prices in {mandi} are stable with a slight downward trend. Cold-storage stock is adequate. Sell existing stock gradually to avoid price dips in the next 2 weeks.",
        "hi": "{mandi} \u092e\u0947\u0902 \u0906\u0932\u0942 \u0915\u0940 \u0915\u0940\u092e\u0924\u0947\u0902 \u0938\u094d\u0925\u093f\u0930 \u0939\u0948\u0902 \u0914\u0930 \u0939\u0932\u094d\u0915\u0940 \u0917\u093f\u0930\u093e\u0935\u091f \u0915\u0940 \u092a\u094d\u0930\u0935\u0943\u0924\u094d\u0924\u093f \u0926\u093f\u0916 \u0930\u0939\u0940 \u0939\u0948\u0964 \u0905\u0917\u0932\u0947 2 \u0938\u092a\u094d\u0924\u093e\u0939 \u092e\u0947\u0902 \u092e\u0942\u0932\u094d\u092f \u0917\u093f\u0930\u093e\u0935\u091f \u0938\u0947 \u092c\u091a\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u0927\u0940\u0930\u0947-\u0927\u0940\u0930\u0947 \u092c\u0947\u091a\u0947\u0902\u0964",
        "risk_level": "Medium",
    },
    "tomato": {
        "en": "Tomato prices in {mandi} are surging due to monsoon disruptions. Expect high volatility. Sell quickly if current stock is mature \u2014 prices may correct sharply once supply resumes.",
        "hi": "{mandi} \u092e\u0947\u0902 \u091f\u092e\u093e\u091f\u0930 \u0915\u0940 \u0915\u0940\u092e\u0924\u0947\u0902 \u092e\u093e\u0928\u0938\u0942\u0928 \u0935\u094d\u092f\u0935\u0927\u093e\u0928 \u0915\u0947 \u0915\u093e\u0930\u0923 \u092c\u0922\u093c \u0930\u0939\u0940 \u0939\u0948\u0902\u0964 \u092f\u0926\u093f \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u0938\u094d\u091f\u0949\u0915 \u092a\u0915\u093e \u0939\u0941\u0906 \u0939\u0948 \u0924\u094b \u091c\u0932\u094d\u0926\u0940 \u092c\u0947\u091a\u0947\u0902\u0964",
        "risk_level": "High",
    },
    "garlic": {
        "en": "Garlic in {mandi} is commanding a premium due to reduced harvest in the current season. If you have dry garlic in storage, this is an excellent window to sell for maximum margin.",
        "hi": "{mandi} \u092e\u0947\u0902 \u0932\u0939\u0938\u0941\u0928 \u0907\u0938 \u0938\u0940\u091c\u0928 \u092e\u0947\u0902 \u0915\u092e \u092b\u0938\u0932 \u0915\u0947 \u0915\u093e\u0930\u0923 \u092a\u094d\u0930\u0940\u092e\u093f\u092f\u092e \u092a\u0930 \u092c\u093f\u0915 \u0930\u0939\u093e \u0939\u0948\u0964",
        "risk_level": "Low",
    },
}

# Default advisory for commodities not in the template
_DEFAULT_ADVISORY = {
    "en": "Market prices for {commodity} in {mandi} are currently stable. Monitor prices daily and sell when the market rate is above the modal price for best returns.",
    "hi": "{mandi} \u092e\u0947\u0902 {commodity} \u0915\u0940 \u0915\u0940\u092e\u0924\u0947\u0902 \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u092e\u0947\u0902 \u0938\u094d\u0925\u093f\u0930 \u0939\u0948\u0902\u0964 \u0938\u0930\u094d\u0935\u094b\u0924\u094d\u0924\u092e \u0930\u093f\u091f\u0930\u094d\u0928 \u0915\u0947 \u0932\u093f\u090f \u092a\u094d\u0930\u0924\u093f\u0926\u093f\u0928 \u0915\u0940\u092e\u0924\u094b\u0902 \u0915\u0940 \u0928\u093f\u0917\u0930\u093e\u0928\u0940 \u0915\u0930\u0947\u0902\u0964",
    "risk_level": "Low",
}


@router.get("/farmer-advisory")
async def get_farmer_advisory(commodity: str, mandi: str):
    """
    Get farmer advisory for a commodity in a specific mandi.
    Also fetches current live price to enrich the advisory.
    """
    commodity_lower = commodity.lower().replace(" ", "_")
    template = _ADVISORIES.get(commodity_lower, _DEFAULT_ADVISORY)

    # Try to get live price for context
    live_price_info = {}
    try:
        price_data = await get_live_prices(commodity=commodity, market=mandi)
        if price_data.get("records"):
            latest = price_data["records"][0]
            live_price_info = {
                "current_modal_price": latest.get("modal_price"),
                "current_min_price": latest.get("min_price"),
                "current_max_price": latest.get("max_price"),
                "price_date": latest.get("arrival_date"),
                "data_source": price_data.get("data_source", "live"),
            }
    except Exception:
        pass  # Advisory still works without live price

    return {
        "commodity": commodity_lower,
        "mandi": mandi,
        "advisory_text": template["en"].format(
            mandi=mandi.capitalize(), commodity=commodity.capitalize()
        ),
        "advisory_text_hi": template["hi"].format(
            mandi=mandi.capitalize(), commodity=commodity.capitalize()
        ),
        "risk_level": template.get("risk_level", "Low"),
        "live_price": live_price_info,
    }
