"""
KisanMitra AI — Market Data Service
Business logic layer between routes and the AGMARKNET API service.

Responsibilities:
- Queries API or falls back to MongoDB cache
- Stores fresh API responses into MongoDB for historical accumulation
- Serves latest cached data when API is down
- Provides aggregated price data per commodity per market
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_async_collection, get_sync_collection, get_database
from services.agmarknet_service import (
    fetch_market_prices,
    fetch_all_market_prices,
    fetch_available_states,
    fetch_districts_for_state,
    fetch_markets_for_district,
    fetch_commodities_for_market,
)
from utils.cache import price_cache
from utils.logger import get_logger
from utils.feature_engineering import create_features
import pandas as pd

logger = get_logger("MarketDataService")


# ---------------------------------------------------------------------------
# MongoDB persistence — store API data for historical accumulation
# ---------------------------------------------------------------------------
async def _persist_prices_to_db(records: list[dict]):
    """
    Upsert price records into MongoDB for historical accumulation.
    Uses commodity + market + arrival_date as the unique key.
    """
    if not records:
        return

    collection = get_async_collection("market_prices")
    persisted = 0

    for doc in records:
        try:
            # Build the filter for upsert
            filter_doc = {
                "commodity_key": doc.get("commodity_key", doc.get("commodity", "").lower().replace(" ", "_")),
                "market": doc["market"],
                "arrival_date": doc["arrival_date"],
            }

            # Store the full document
            update_doc = {
                "$set": {
                    "commodity": doc["commodity"],
                    "commodity_key": doc.get("commodity_key", doc.get("commodity", "").lower().replace(" ", "_")),
                    "state": doc["state"],
                    "district": doc.get("district", ""),
                    "market": doc["market"],
                    "variety": doc.get("variety", ""),
                    "grade": doc.get("grade", ""),
                    "min_price": doc.get("min_price"),
                    "max_price": doc.get("max_price"),
                    "modal_price": doc.get("modal_price"),
                    "price": doc.get("modal_price"),  # alias for ML pipeline compat
                    "date": doc["arrival_date"],  # alias for ML pipeline compat
                    "arrival_date": doc["arrival_date"],
                    "source": doc.get("source", "agmarknet_live"),
                    "fetched_at": doc.get("fetched_at", datetime.utcnow().isoformat()),
                }
            }

            await collection.update_one(filter_doc, update_doc, upsert=True)
            persisted += 1
        except Exception as e:
            logger.error(f"Failed to persist price record: {e}")

    if persisted > 0:
        logger.info(f"Persisted {persisted} price records to MongoDB")
        # Update engineered features for each unique commodity/mandi combination
        updated_combos = set((doc["commodity"], doc["market"]) for doc in records)
        db = get_database()
        for commodity, mandi in updated_combos:
            await update_engineered_features(commodity, mandi, db)

async def update_engineered_features(commodity: str, mandi: str, db):
    # Fetch last 90 days from market_prices for this combo
    cursor = db.market_prices.find(
        {"commodity": commodity, "market": mandi},
        sort=[("arrival_date", -1)],
        limit=90
    )
    records = await cursor.to_list(length=90)
    
    if len(records) < 30:
        return  # not enough data to engineer features
    
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["arrival_date"])
    df["modal_price"] = pd.to_numeric(
        df["modal_price"], errors="coerce"
    )
    df = df.sort_values("date").dropna(
        subset=["modal_price"]
    )
    
    engineered = create_features(df)
    if engineered.empty:
        return
    
    # Save latest engineered row to engineered_features
    latest_row = engineered.iloc[-1].to_dict()
    latest_row["commodity"] = commodity
    latest_row["mandi"] = mandi
    latest_row["updated_at"] = pd.Timestamp.now()
    
    await db.engineered_features.update_one(
        {"commodity": commodity, "mandi": mandi},
        {"$set": latest_row},
        upsert=True
    )


async def _persist_metadata_to_db(data_type: str, values: list, parent_filters: dict = None):
    """
    Store market metadata (states/districts/markets/commodities) in MongoDB.
    """
    collection = get_async_collection("market_metadata")
    doc = {
        "type": data_type,
        "values": values,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if parent_filters:
        doc.update(parent_filters)

    filter_doc = {"type": data_type}
    if parent_filters:
        filter_doc.update(parent_filters)

    await collection.update_one(filter_doc, {"$set": doc}, upsert=True)


# ---------------------------------------------------------------------------
# Public API — used by routes
# ---------------------------------------------------------------------------
async def get_states() -> list[str]:
    """Get all available states, with DB fallback."""
    try:
        states = await fetch_available_states()
        if states:
            await _persist_metadata_to_db("states", states)
            return states
    except Exception as e:
        logger.error(f"Failed to fetch states from API: {e}")

    # Fallback to MongoDB
    collection = get_async_collection("market_metadata")
    doc = await collection.find_one({"type": "states"})
    if doc and doc.get("values"):
        logger.info("Serving states from MongoDB cache")
        return doc["values"]

    # Secondary fallback: extract distinct from market_prices
    try:
        prices_coll = get_async_collection("market_prices")
        states = await prices_coll.distinct("State")
        if not states:
            states = await prices_coll.distinct("state")
        if states:
            logger.info("Serving states from MongoDB prices fallback")
            return sorted(set(s for s in states if s))
    except Exception as e:
        logger.error(f"Secondary fallback failed: {e}")

    return []


async def get_districts(state: str) -> list[str]:
    """Get districts for a state, with DB fallback."""
    try:
        districts = await fetch_districts_for_state(state)
        if districts:
            await _persist_metadata_to_db("districts", districts, {"state": state})
            return districts
    except Exception as e:
        logger.error(f"Failed to fetch districts from API: {e}")

    # Fallback
    collection = get_async_collection("market_metadata")
    doc = await collection.find_one({"type": "districts", "state": state})
    if doc and doc.get("values"):
        logger.info(f"Serving districts for {state} from MongoDB cache")
        return doc["values"]

    # Secondary fallback: extract distinct from market_prices
    try:
        prices_coll = get_async_collection("market_prices")
        districts = await prices_coll.distinct("District", {"State": state})
        if not districts:
            districts = await prices_coll.distinct("district", {"state": state})
        if districts:
            logger.info("Serving districts from MongoDB prices fallback")
            return sorted(set(d for d in districts if d))
    except Exception as e:
        logger.error(f"Secondary fallback failed: {e}")

    return []


async def get_markets(state: str, district: str) -> list[str]:
    """Get markets for a district, with DB fallback."""
    try:
        markets = await fetch_markets_for_district(state, district)
        if markets:
            await _persist_metadata_to_db(
                "markets", markets, {"state": state, "district": district}
            )
            return markets
    except Exception as e:
        logger.error(f"Failed to fetch markets from API: {e}")

    # Fallback
    collection = get_async_collection("market_metadata")
    doc = await collection.find_one(
        {"type": "markets", "state": state, "district": district}
    )
    if doc and doc.get("values"):
        logger.info(f"Serving markets for {state}/{district} from MongoDB cache")
        return doc["values"]

    # Secondary fallback: extract distinct from market_prices
    try:
        prices_coll = get_async_collection("market_prices")
        markets = await prices_coll.distinct("Market", {"State": state, "District": district})
        if not markets:
            markets = await prices_coll.distinct("market", {"state": state, "district": district})
        if markets:
            logger.info("Serving markets from MongoDB prices fallback")
            return sorted(set(m for m in markets if m))
    except Exception as e:
        logger.error(f"Secondary fallback failed: {e}")

    return []


async def get_commodities(state: str, market: str) -> list[str]:
    """Get commodities for a market, with DB fallback."""
    try:
        commodities = await fetch_commodities_for_market(state, market)
        if commodities:
            await _persist_metadata_to_db(
                "commodities", commodities, {"state": state, "market": market}
            )
            return commodities
    except Exception as e:
        logger.error(f"Failed to fetch commodities from API: {e}")

    # Fallback
    collection = get_async_collection("market_metadata")
    doc = await collection.find_one(
        {"type": "commodities", "state": state, "market": market}
    )
    if doc and doc.get("values"):
        logger.info(f"Serving commodities for {state}/{market} from MongoDB cache")
        return doc["values"]

    # Secondary fallback: extract distinct from market_prices
    try:
        prices_coll = get_async_collection("market_prices")
        commodities = await prices_coll.distinct("commodity", {"State": state, "Market": market})
        if not commodities:
            commodities = await prices_coll.distinct("commodity", {"state": state, "market": market})
        if commodities:
            logger.info("Serving commodities from MongoDB prices fallback")
            # Capitalize first letter to match frontend expectations typically
            return sorted(set(c.title() for c in commodities if c))
    except Exception as e:
        logger.error(f"Secondary fallback failed: {e}")

    return []


async def get_live_prices(
    state: Optional[str] = None,
    district: Optional[str] = None,
    market: Optional[str] = None,
    commodity: Optional[str] = None,
) -> dict:
    """
    Get live market prices. Returns dict with data_source indicator.
    Persists results to MongoDB for historical accumulation.
    """
    cache_key = f"live:{state}:{district}:{market}:{commodity}"
    cached = price_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        records = await fetch_all_market_prices(
            state=state,
            district=district,
            market=market,
            commodity=commodity,
            max_pages=5,
        )

        if records:
            # Persist to MongoDB for historical accumulation
            await _persist_prices_to_db(records)

            result = {
                "data_source": "live",
                "records": records,
                "count": len(records),
                "fetched_at": datetime.utcnow().isoformat(),
            }
            price_cache.set(cache_key, result)
            return result

    except Exception as e:
        logger.error(f"Failed to fetch live prices: {e}")

    # Fallback to MongoDB
    return await _get_cached_prices(state, district, market, commodity)


async def _get_cached_prices(
    state: Optional[str] = None,
    district: Optional[str] = None,
    market: Optional[str] = None,
    commodity: Optional[str] = None,
) -> dict:
    """
    Fetch the latest cached prices from MongoDB.
    Used when the live API is unavailable.
    """
    collection = get_async_collection("market_prices")

    query = {}
    if state:
        query["state"] = state
    if district:
        query["district"] = district
    if market:
        query["market"] = market
    if commodity:
        # Match both exact and normalized commodity key
        query["$or"] = [
            {"commodity": commodity},
            {"commodity_key": commodity.lower().replace(" ", "_")},
        ]

    try:
        cursor = collection.find(query, {"_id": 0}).sort("arrival_date", -1).limit(500)
        records = await cursor.to_list(length=500)

        if records:
            logger.info(
                f"Serving {len(records)} cached prices from MongoDB "
                f"(API unavailable)"
            )
            return {
                "data_source": "cached",
                "message": "Showing latest available verified market prices.",
                "records": records,
                "count": len(records),
                "fetched_at": records[0].get("fetched_at", "unknown"),
            }
    except Exception as e:
        logger.error(f"Failed to fetch cached prices: {e}")

    return {
        "data_source": "unavailable",
        "message": "Market price data is temporarily unavailable. Please try again.",
        "records": [],
        "count": 0,
    }


async def get_latest_commodity_prices() -> list[dict]:
    """
    Get the latest price for each commodity across all markets.
    Used by the dashboard commodities endpoint.
    """
    cache_key = "latest_commodity_prices"
    cached = price_cache.get(cache_key)
    if cached is not None:
        return cached

    # Try fetching fresh from API (broad query)
    try:
        records = await fetch_market_prices(limit=1000)
        if records:
            await _persist_prices_to_db(records)
    except Exception:
        records = []

    # If no API data, fall back to MongoDB
    if not records:
        collection = get_async_collection("market_prices")
        try:
            cursor = collection.find({}, {"_id": 0}).sort("arrival_date", -1).limit(1000)
            records = await cursor.to_list(length=1000)
        except Exception as e:
            logger.error(f"Failed to fetch commodity prices from DB: {e}")
            return []

    # Aggregate: get latest price per commodity
    commodity_map = {}
    for r in records:
        ckey = r.get("commodity_key") or r.get("commodity", "").lower().replace(" ", "_")
        if ckey not in commodity_map:
            commodity_map[ckey] = {
                "commodity": r.get("commodity", ckey),
                "commodity_key": ckey,
                "modal_price": r.get("modal_price") or r.get("price", 0),
                "min_price": r.get("min_price"),
                "max_price": r.get("max_price"),
                "market": r.get("market", ""),
                "state": r.get("state", ""),
                "district": r.get("district", ""),
                "arrival_date": r.get("arrival_date") or r.get("date", ""),
                "source": r.get("source", "agmarknet"),
            }

    result = list(commodity_map.values())
    price_cache.set(cache_key, result, ttl_seconds=600)
    return result
