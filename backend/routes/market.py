"""
market.py — Agmarknet market data with 3-tier fallback:
  1. Live Agmarknet API (10s timeout)
  2. MongoDB cached data (auto-saved when API succeeds)
  3. Hardcoded fallback lists
"""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Query
import httpx

from database import get_async_collection

router = APIRouter()

AGMARKNET_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# ─── Fallback lists ───────────────────────────────────────────────────────────

FALLBACK_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Keralam",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

FALLBACK_DISTRICTS_MH = [
    "Nashik", "Pune", "Kolhapur", "Aurangabad",
    "Nagpur", "Solapur", "Satara", "Sangli", "Ahmednagar",
    "Jalgaon", "Latur", "Amravati", "Wardha", "Yavatmal",
]

FALLBACK_MANDIS_NASHIK = [
    "Nashik", "Lasalgaon", "Pimpalgaon", "Niphad", "Chandwad",
    "Malegaon", "Satana", "Manmad", "Yeola", "Nandgaon",
]

FALLBACK_COMMODITIES = [
    "Onion", "Tomato", "Potato", "Wheat", "Rice", "Maize", "Chilli",
    "Garlic", "Ginger", "Turmeric", "Soybean", "Cotton",
    "Groundnut", "Mustard", "Bajra", "Jowar", "Arhar(Tur)",
    "Moong", "Urad", "Gram", "Banana", "Mango",
    "Bhindi(Ladies Finger)", "Brinjal", "Cabbage",
    "Cauliflower", "Peas", "Cucumber",
]

FALLBACK_MAP = {
    "states": FALLBACK_STATES,
}


# ─── MongoDB cache helpers ────────────────────────────────────────────────────

async def save_to_cache(key: str, data, collection_name: str = "market_cache"):
    """Save data to MongoDB cache with timestamp. Never crashes."""
    try:
        cache = get_async_collection(collection_name)
        await cache.update_one(
            {"key": key},
            {"$set": {
                "key": key,
                "data": data,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        print(f"[cache] Saved '{key}' to MongoDB")
    except Exception as e:
        print(f"[cache] Failed to save '{key}': {e}")


async def load_from_cache(key: str, collection_name: str = "market_cache"):
    """Load data from MongoDB cache. Returns None if not found or error."""
    try:
        cache = get_async_collection(collection_name)
        doc = await cache.find_one({"key": key})
        if doc and doc.get("data"):
            print(f"[cache] Hit for '{key}' (cached at {doc.get('cached_at', 'unknown')})")
            return doc["data"]
    except Exception as e:
        print(f"[cache] Failed to read '{key}': {e}")
    return None


# ─── Shared Agmarknet fetch helper ───────────────────────────────────────────

async def fetch_agmarknet(filters: dict | None = None, timeout: float = 10.0) -> list[dict]:
    """
    Paginate through the Agmarknet API and return all matching records.
    Returns empty list on any failure (timeout, network, etc).
    """
    api_key = os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd0000013857b8930c4341a96b96a0494dd13398")
    all_records: list[dict] = []
    offset = 0
    limit = 500

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            while True:
                params: dict = {
                    "api-key": api_key,
                    "format": "json",
                    "limit": limit,
                    "offset": offset,
                }
                if filters:
                    params.update(filters)

                resp = await client.get(AGMARKNET_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                records = data.get("records", [])
                all_records.extend(records)

                if len(records) < limit:
                    break
                offset += limit
    except Exception as e:
        print(f"[market] Agmarknet fetch error: {e}")

    return all_records


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/states")
async def get_states():
    """Return unique states. Try API → MongoDB cache → fallback."""
    cache_key = "states"

    # Tier 1: Try Agmarknet
    records = await fetch_agmarknet()
    if records:
        states = sorted({r.get("state", "") for r in records if r.get("state")})
        if states:
            await save_to_cache(cache_key, states)
            return {"states": states, "source": "live"}

    # Tier 2: Try MongoDB cache
    cached = await load_from_cache(cache_key)
    if cached:
        return {"states": cached, "source": "cache"}

    # Tier 3: Hardcoded fallback
    return {"states": FALLBACK_STATES, "source": "fallback"}


@router.get("/districts")
async def get_districts(state: str = Query(..., description="State name")):
    """Return districts for a given state. Try API → cache → fallback."""
    cache_key = f"districts_{state}"

    # Tier 1: Try Agmarknet
    records = await fetch_agmarknet({"filters[state]": state})
    if records:
        districts = sorted({r.get("district", "") for r in records if r.get("district")})
        if districts:
            await save_to_cache(cache_key, districts)
            return {"districts": districts, "state": state, "source": "live"}

    # Tier 2: Try MongoDB cache
    cached = await load_from_cache(cache_key)
    if cached:
        return {"districts": cached, "state": state, "source": "cache"}

    # Tier 3: Hardcoded fallback (only for Maharashtra)
    if state == "Maharashtra":
        return {"districts": FALLBACK_DISTRICTS_MH, "state": state, "source": "fallback"}

    return {"districts": ["Central District", "North District", "South District"], "state": state, "source": "synthetic"}


@router.get("/mandis")
async def get_mandis(
    state: str = Query(..., description="State name"),
    district: str = Query(..., description="District name"),
):
    """Return mandis for a given state and district. Try API → cache → fallback."""
    cache_key = f"mandis_{state}_{district}"

    # Tier 1: Try Agmarknet
    records = await fetch_agmarknet({
        "filters[state]": state,
        "filters[district]": district,
    })
    if records:
        mandis = sorted({r.get("market", "") for r in records if r.get("market")})
        if mandis:
            await save_to_cache(cache_key, mandis)
            return {"mandis": mandis, "source": "live"}

    # Tier 2: Try MongoDB cache
    cached = await load_from_cache(cache_key)
    if cached:
        return {"mandis": cached, "source": "cache"}

    # Tier 3: Hardcoded fallback (only for Nashik)
    if district == "Nashik":
        return {"mandis": FALLBACK_MANDIS_NASHIK, "source": "fallback"}

    return {"mandis": [f"{district} Main Market", f"{district} APMC"], "source": "synthetic"}


@router.get("/commodities")
async def get_commodities(
    state: str = Query("", description="State name"),
    district: str = Query("", description="District name"),
    market: str = Query("", description="Market/Mandi name"),
):
    """Return commodities at a market. Try API → cache → fallback."""
    cache_key = f"commodities_{state}_{district}_{market}"

    # Tier 1: Try Agmarknet
    filters: dict = {}
    if state:
        filters["filters[state]"] = state
    if district:
        filters["filters[district]"] = district
    if market:
        filters["filters[market]"] = market

    records = await fetch_agmarknet(filters)
    if records:
        commodities = sorted({r.get("commodity", "") for r in records if r.get("commodity")})
        if commodities:
            await save_to_cache(cache_key, commodities)
            return {"commodities": commodities, "source": "live"}

    # Tier 2: Try MongoDB cache
    cached = await load_from_cache(cache_key)
    if cached:
        return {"commodities": cached, "source": "cache"}

    # Tier 3: Hardcoded fallback
    return {"commodities": FALLBACK_COMMODITIES, "source": "fallback"}


@router.get("/prices")
async def get_prices(
    state: str = Query("", description="State name"),
    district: str = Query("", description="District name"),
    market: str = Query("", description="Market/Mandi name"),
    commodity: str = Query("", description="Commodity name"),
):
    """Return raw price records with 3-step fallback. Try API → cache → error message."""
    cache_key = f"prices_{state}_{district}_{market}_{commodity}"

    records = []
    note = ""

    # STEP 1: Try exact match — all provided filters
    if commodity or market:
        filters: dict = {}
        if state:
            filters["filters[state]"] = state
        if district:
            filters["filters[district]"] = district
        if market:
            filters["filters[market]"] = market
        if commodity:
            filters["filters[commodity]"] = commodity
        records = await fetch_agmarknet(filters)

    # STEP 2: If empty, try with only commodity filter (drop market)
    if not records and commodity:
        filters = {}
        if state:
            filters["filters[state]"] = state
        filters["filters[commodity]"] = commodity
        records = await fetch_agmarknet(filters)
        if records:
            note = "Showing broader market data — exact market not found in today's dataset"

    # STEP 3: If still empty, try with just the state
    if not records:
        fallback_state = state or "Maharashtra"
        records = await fetch_agmarknet({"filters[state]": fallback_state})
        if records:
            note = "Showing broader market data — exact market not found in today's dataset"

    if records:
        prices = []
        for r in records:
            prices.append({
                "state": r.get("state", ""),
                "district": r.get("district", ""),
                "market": r.get("market", ""),
                "commodity": r.get("commodity", ""),
                "variety": r.get("variety", ""),
                "min_price": r.get("min_price", ""),
                "max_price": r.get("max_price", ""),
                "modal_price": r.get("modal_price", ""),
                "date": r.get("arrival_date", ""),
            })
        # Save to cache
        await save_to_cache(cache_key, prices, collection_name="price_cache")
        result = {"prices": prices, "total": len(prices), "source": "live"}
        if note:
            result["note"] = note
        return result

    # Tier 2: Try MongoDB price_cache
    cached = await load_from_cache(cache_key, collection_name="price_cache")
    if cached:
        return {"prices": cached, "total": len(cached), "source": "cache"}

    # Tier 3: Fall back to market_prices collection (imported CSV data)
    try:
        mp_collection = get_async_collection("market_prices")
        query: dict = {}
        if commodity:
            query["commodity"] = {"$regex": f"^{commodity.strip()}$", "$options": "i"}
        if market:
            query["market"] = {"$regex": f"^{market.strip()}$", "$options": "i"}
        if state:
            query["state"] = {"$regex": f"^{state.strip()}$", "$options": "i"}
        if district:
            query["district"] = {"$regex": f"^{district.strip()}$", "$options": "i"}

        cursor = mp_collection.find(query, {"_id": 0}).sort("date", -1).limit(200)
        mp_records = await cursor.to_list(length=200)

        if mp_records:
            prices = [
                {
                    "state": r.get("state", state),
                    "district": r.get("district", district),
                    "market": r.get("market", market),
                    "commodity": r.get("commodity", commodity),
                    "variety": r.get("variety", ""),
                    "min_price": r.get("min_price", r.get("price", "")),
                    "max_price": r.get("max_price", r.get("price", "")),
                    "modal_price": r.get("modal_price", r.get("price", "")),
                    "date": str(r.get("date", ""))[:10],
                }
                for r in mp_records
            ]
            return {
                "prices": prices,
                "total": len(prices),
                "source": "historical_db",
                "note": "Showing historical data — live API temporarily unavailable",
            }
    except Exception as e:
        print(f"[market] Failed to query market_prices fallback: {e}")

    # Tier 4: No data available
    return {
        "prices": [],
        "message": "Price data temporarily unavailable. Government API is slow.",
        "count": 0,
        "source": "unavailable",
    }
