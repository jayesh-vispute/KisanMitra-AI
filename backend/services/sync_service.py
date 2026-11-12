import asyncio
import logging
from datetime import datetime, timezone
from database import get_async_collection
from services.agmarknet_service import fetch_available_states, fetch_districts_for_state, fetch_markets_for_district, fetch_commodities_for_market

logger = logging.getLogger("SyncService")

async def sync_market_metadata():
    """
    Background task to sync state, district, and mandi metadata from Agmarknet API to MongoDB.
    This runs periodically to keep the dropdowns up to date without blocking user requests.
    """
    try:
        logger.info("Starting background metadata sync from Agmarknet...")
        collection = get_async_collection("market_metadata")
        
        # 1. Sync States
        states = await fetch_available_states()
        if states:
            await collection.update_one(
                {"type": "states"},
                {"$set": {"data": states, "updated_at": datetime.now(timezone.utc)}},
                upsert=True
            )
            logger.info(f"Synced {len(states)} states.")
            
            # 2. Sync Districts for each State
            for state in states:
                districts = await fetch_districts_for_state(state)
                if districts:
                    await collection.update_one(
                        {"type": "districts", "state": state},
                        {"$set": {"data": districts, "updated_at": datetime.now(timezone.utc)}},
                        upsert=True
                    )
                    
                    # Optional: Sync Mandis for each district (This can take a very long time, so we might want to rate limit or do it in chunks)
                    # For phase 1, we will skip deep mandi syncing to avoid rate limiting loops, relying on the fallback or on-demand fetch if needed.
                    # A better approach is fetching all records once and extracting.
        
        logger.info("Background metadata sync completed successfully.")
    except Exception as e:
        logger.error(f"Background metadata sync failed: {e}")

async def start_background_sync(interval_seconds: int = 86400):
    """Start the periodic background sync task."""
    while True:
        await sync_market_metadata()
        await asyncio.sleep(interval_seconds)
