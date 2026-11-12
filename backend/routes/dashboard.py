"""
KisanMitra AI — Dashboard Summary Route
Returns real-time trust-signal data: timestamps, model accuracy, market status,
data freshness — all from live AGMARKNET data stored in MongoDB.
"""

from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

from database import get_async_collection
from services.market_data_service import get_latest_commodity_prices
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("DashboardRoute")

IST = timezone(timedelta(hours=5, minutes=30))


def _get_market_status():
    """Return market status based on current IST time."""
    now = datetime.now(IST)
    hour = now.hour
    if 9 <= hour < 18:
        return "open"
    elif 7 <= hour < 9:
        return "pre-market"
    else:
        return "closed"


@router.get("/dashboard/summary")
async def get_dashboard_summary():
    now = datetime.now(IST)
    metrics_collection = get_async_collection("model_metrics")
    market_collection = get_async_collection("market_prices")

    # Fetch model metrics from MongoDB
    metrics_doc = await metrics_collection.find_one({"type": "metrics"})
    metrics = metrics_doc.get("data", {}) if metrics_doc else {}

    # Fetch data quality
    data_quality_doc = await metrics_collection.find_one({"type": "data_quality"})
    data_quality = (
        data_quality_doc
        if data_quality_doc
        else {
            "live_data_active": False,
            "agmarknet_last_fetch": None,
            "total": {"real_percentage": "0.0%"},
        }
    )

    # ---------------------------------------------------------------------------
    # Get REAL commodity counts and mandi counts from MongoDB
    # ---------------------------------------------------------------------------
    try:
        distinct_commodities = await market_collection.distinct("commodity_key")
        distinct_mandis = await market_collection.distinct("market")
        distinct_states = await market_collection.distinct("state")
    except Exception as e:
        logger.error(f"Failed to query market_prices collection: {e}")
        distinct_commodities = []
        distinct_mandis = []
        distinct_states = []

    # Get latest commodity prices for display
    try:
        commodity_prices = await get_latest_commodity_prices()
    except Exception:
        commodity_prices = []

    # ---------------------------------------------------------------------------
    # Model accuracy for all commodities (from trained models)
    # ---------------------------------------------------------------------------
    model_accuracy = {}
    for commodity_data in commodity_prices:
        c = commodity_data.get("commodity_key", "")
        if c in metrics:
            ens = metrics.get(c, {}).get("Ensemble", {})
            mape_val = ens.get("MAPE", 5.0)
            model_accuracy[c] = {
                "ensemble_mape": round(mape_val, 2),
                "confidence": round(100 - mape_val, 2),
            }
        else:
            model_accuracy[c] = {
                "ensemble_mape": 0,
                "confidence": 0,
                "note": "Model not yet trained for this commodity",
            }

    # ---------------------------------------------------------------------------
    # Data freshness — computed from REAL fetched_at timestamps in MongoDB
    # ---------------------------------------------------------------------------
    data_freshness = {}
    try:
        # Get the latest record for each market
        pipeline = [
            {"$sort": {"fetched_at": -1}},
            {
                "$group": {
                    "_id": "$market",
                    "last_fetched": {"$first": "$fetched_at"},
                    "last_date": {"$first": "$arrival_date"},
                    "state": {"$first": "$state"},
                }
            },
            {"$limit": 50},
        ]
        cursor = market_collection.aggregate(pipeline)
        async for doc in cursor:
            market_name = doc.get("_id", "")
            if not market_name:
                continue

            last_fetched = doc.get("last_fetched", "")
            if last_fetched:
                try:
                    fetched_dt = datetime.fromisoformat(last_fetched)
                    hours_ago = (datetime.utcnow() - fetched_dt).total_seconds() / 3600
                    status = (
                        "fresh"
                        if hours_ago < 24
                        else ("stale" if hours_ago < 48 else "outdated")
                    )
                except (ValueError, TypeError):
                    hours_ago = None
                    status = "unknown"
            else:
                hours_ago = None
                status = "unknown"

            data_freshness[market_name] = {
                "last_updated": last_fetched,
                "last_market_date": doc.get("last_date", ""),
                "hours_ago": round(hours_ago, 1) if hours_ago is not None else None,
                "status": status,
                "state": doc.get("state", ""),
            }
    except Exception as e:
        logger.error(f"Failed to compute data freshness: {e}")

    # ---------------------------------------------------------------------------
    # Alerts based on REAL price data
    # ---------------------------------------------------------------------------
    alerts = []
    for item in commodity_prices:
        modal = item.get("modal_price") or item.get("price", 0)
        min_p = item.get("min_price", 0)
        if modal and min_p and min_p > 0:
            spread_pct = ((modal - min_p) / min_p) * 100
            if spread_pct > 15:
                alerts.append({
                    "commodity": item.get("commodity", ""),
                    "level": "CRITICAL",
                    "market": item.get("market", ""),
                })
            elif spread_pct > 8:
                alerts.append({
                    "commodity": item.get("commodity", ""),
                    "level": "HIGH",
                    "market": item.get("market", ""),
                })

    return {
        "last_updated": now.isoformat(),
        "data_sources": ["Agmarknet (Live)", "Open-Meteo", "NASA MODIS"],
        "total_mandis": len(distinct_mandis),
        "total_commodities": len(distinct_commodities),
        "total_states": len(distinct_states),
        "model_accuracy": model_accuracy,
        "market_status": _get_market_status(),
        "data_freshness": data_freshness,
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["level"] == "CRITICAL"]),
        "alerts_detail": alerts,
        "live_data_active": data_quality.get("live_data_active", False),
        "agmarknet_last_fetch": data_quality.get("agmarknet_last_fetch"),
        "real_data_coverage": f"{data_quality.get('total', {}).get('real_percentage', '0.0%')} of training data from live Agmarknet feed",
    }
