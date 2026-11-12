"""
KisanMitra AI — AGMARKNET Scraper Service
Handles all communication with the Agmarknet website via the new scraper.
Replaces the deprecated data.gov.in AGMARKNET API.

Responsibilities:
- Run synchronous scraper in asyncio thread pool
- Pagination
- Data normalization (field names, dates, types)
- Response caching (in-memory TTL + MongoDB persistence)
- Structured logging
"""

import os
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException

from utils.cache import api_cache, metadata_cache
from utils.logger import get_logger, log_api_call
from data_ingestion.agmarknet_scraper import scraper

logger = get_logger("AgmarknetService")

# ---------------------------------------------------------------------------
# Core Scraper fetch with async wrapping
# ---------------------------------------------------------------------------
async def _fetch_scraper(state="", district="", market="", commodity="", max_pages=3) -> list[dict]:
    """
    Run the synchronous scraper in an async executor to avoid blocking the event loop.
    """
    try:
        # Run synchronous scraper in a separate thread
        records = await asyncio.to_thread(
            scraper.scrape_latest_prices,
            state=state,
            district=district,
            market=market,
            commodity=commodity,
            max_pages=max_pages
        )
        return records
    except Exception as e:
        logger.error(f"Scraper fetch failed: {e}")
        return []

# ---------------------------------------------------------------------------
# Public API methods
# ---------------------------------------------------------------------------
@log_api_call("AgmarknetScraper")
async def fetch_market_prices(
    state: Optional[str] = None,
    district: Optional[str] = None,
    market: Optional[str] = None,
    commodity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Fetch current market prices from AGMARKNET Scraper.
    Supports filtering by state, district, market, commodity.
    Returns normalized list of price records.
    """
    # Build cache key
    cache_key = f"prices:{state}:{district}:{market}:{commodity}:{limit}:{offset}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached

    # Estimate max pages based on limit + offset. Scraper gives ~50 rows per page.
    max_pages = (limit + offset) // 50 + 1

    records = await _fetch_scraper(
        state=state or "",
        district=district or "",
        market=market or "",
        commodity=commodity or "",
        max_pages=max_pages
    )
    
    if not records:
        return []

    # Slice the results based on offset and limit
    sliced_records = records[offset : offset + limit]

    api_cache.set(cache_key, sliced_records)
    return sliced_records


@log_api_call("AgmarknetScraper")
async def fetch_all_market_prices(
    state: Optional[str] = None,
    district: Optional[str] = None,
    market: Optional[str] = None,
    commodity: Optional[str] = None,
    max_pages: int = 10,
) -> list[dict]:
    """
    Fetch all available prices.
    """
    return await _fetch_scraper(
        state=state or "",
        district=district or "",
        market=market or "",
        commodity=commodity or "",
        max_pages=max_pages
    )


@log_api_call("AgmarknetScraper")
async def fetch_available_states() -> list[str]:
    """
    Fetch all available states from AGMARKNET.
    """
    cache_key = "metadata:states"
    cached = metadata_cache.get(cache_key)
    if cached is not None:
        return cached

    records = await _fetch_scraper(max_pages=3)
    if not records:
        return []

    states = sorted(set(
        (r.get("state") or "").strip()
        for r in records
        if (r.get("state") or "").strip()
    ))

    metadata_cache.set(cache_key, states)
    return states


@log_api_call("AgmarknetScraper")
async def fetch_districts_for_state(state: str) -> list[str]:
    """Fetch all districts available in a given state."""
    cache_key = f"metadata:districts:{state}"
    cached = metadata_cache.get(cache_key)
    if cached is not None:
        return cached

    records = await _fetch_scraper(state=state, max_pages=3)
    if not records:
        return []

    districts = sorted(set(
        (r.get("district") or "").strip()
        for r in records
        if (r.get("district") or "").strip()
    ))

    metadata_cache.set(cache_key, districts)
    return districts


@log_api_call("AgmarknetScraper")
async def fetch_markets_for_district(state: str, district: str) -> list[str]:
    """Fetch all markets (mandis) available in a given district."""
    cache_key = f"metadata:markets:{state}:{district}"
    cached = metadata_cache.get(cache_key)
    if cached is not None:
        return cached

    records = await _fetch_scraper(state=state, district=district, max_pages=3)
    if not records:
        return []

    markets = sorted(set(
        (r.get("market") or "").strip()
        for r in records
        if (r.get("market") or "").strip()
    ))

    metadata_cache.set(cache_key, markets)
    return markets


@log_api_call("AgmarknetScraper")
async def fetch_commodities_for_market(
    state: str, market: str
) -> list[str]:
    """Fetch all commodities available in a given market."""
    cache_key = f"metadata:commodities:{state}:{market}"
    cached = metadata_cache.get(cache_key)
    if cached is not None:
        return cached

    records = await _fetch_scraper(state=state, market=market, max_pages=3)
    if not records:
        return []

    commodities = sorted(set(
        (r.get("commodity") or "").strip()
        for r in records
        if (r.get("commodity") or "").strip()
    ))

    metadata_cache.set(cache_key, commodities)
    return commodities


def get_cache_stats() -> dict:
    """Return cache statistics for monitoring."""
    return {
        "api_cache": api_cache.stats,
        "metadata_cache": metadata_cache.stats,
    }
