"""
KisanMitra AI — Alerts Route
Generates alerts based on REAL price data from MongoDB (populated by AGMARKNET API).
No more random/hardcoded alert generation.
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta

from database import get_async_collection
from utils.cache import price_cache
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("AlertsRoute")

IST = timezone(timedelta(hours=5, minutes=30))


@router.get("/alerts")
async def get_alerts(commodity: Optional[str] = None, level: Optional[str] = None):
    """
    Generate alerts based on real price movements from the market_prices collection.
    Compares latest prices against recent averages to detect volatility.
    """
    now = datetime.now(IST)
    collection = get_async_collection("market_prices")

    alerts = []

    try:
        # Get distinct commodities from DB
        if commodity:
            commodities_to_check = [commodity.lower().replace(" ", "_")]
        else:
            commodities_to_check = await collection.distinct("commodity_key")
            if not commodities_to_check:
                # Fallback: try 'commodity' field
                commodities_to_check = await collection.distinct("commodity")

        for c_key in commodities_to_check:
            if not c_key:
                continue

            # Find the latest price for this commodity
            query = {"$or": [{"commodity_key": c_key}, {"commodity": c_key}]}
            latest = await collection.find_one(
                query, {"_id": 0}, sort=[("arrival_date", -1)]
            )

            if not latest:
                continue

            modal_price = latest.get("modal_price") or latest.get("price", 0)
            min_price = latest.get("min_price", 0)
            max_price = latest.get("max_price", 0)
            market = latest.get("market", "")
            state = latest.get("state", "")
            arrival_date = latest.get("arrival_date") or latest.get("date", "")

            if not modal_price or modal_price <= 0:
                continue

            # Compute price spread as volatility indicator
            if min_price and min_price > 0:
                spread_pct = ((modal_price - min_price) / min_price) * 100
            else:
                spread_pct = 0

            # Also try to compare with historical average from last 7 entries
            hist_cursor = collection.find(
                query, {"modal_price": 1, "price": 1, "_id": 0}
            ).sort("arrival_date", -1).limit(7)
            hist_docs = await hist_cursor.to_list(length=7)
            hist_prices = [
                d.get("modal_price") or d.get("price", 0) for d in hist_docs
                if (d.get("modal_price") or d.get("price", 0)) > 0
            ]

            if len(hist_prices) >= 2:
                avg_price = sum(hist_prices) / len(hist_prices)
                if avg_price > 0:
                    change_from_avg = ((modal_price - avg_price) / avg_price) * 100
                else:
                    change_from_avg = 0
            else:
                avg_price = modal_price
                change_from_avg = spread_pct  # Use spread as fallback

            # Determine alert level based on actual price deviation
            if abs(change_from_avg) > 15 or spread_pct > 20:
                lvl = "CRITICAL"
            elif abs(change_from_avg) > 8 or spread_pct > 12:
                lvl = "HIGH"
            else:
                continue  # No alert needed

            alerts.append({
                "commodity": latest.get("commodity", c_key),
                "commodity_key": c_key,
                "mandi": market,
                "state": state,
                "alert_level": lvl,
                "trigger_price": round(modal_price),
                "avg_price": round(avg_price),
                "min_price": round(min_price) if min_price else None,
                "max_price": round(max_price) if max_price else None,
                "change_pct": round(change_from_avg, 1),
                "spread_pct": round(spread_pct, 1),
                "forecast_date": arrival_date,
                "data_source": "agmarknet_live",
            })

    except Exception as e:
        logger.error(f"Failed to generate alerts: {e}")

    # Apply filters
    filtered = alerts
    if commodity:
        c_lower = commodity.lower().replace(" ", "_")
        filtered = [a for a in filtered if a["commodity_key"] == c_lower or a["commodity"].lower() == commodity.lower()]
    if level:
        filtered = [a for a in filtered if a["alert_level"] == level.upper()]

    # Sort: CRITICAL first, then HIGH
    level_order = {"CRITICAL": 0, "HIGH": 1}
    filtered.sort(key=lambda x: level_order.get(x["alert_level"], 2))

    return {"alerts": filtered, "data_source": "live"}
