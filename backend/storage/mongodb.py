import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_sync_collection

logger = logging.getLogger(__name__)


def save_weather_cache(records):
    """
    Saves or updates weather records in MongoDB to serve as a fallback cache.
    """
    if not records:
        return

    try:
        coll = get_sync_collection("weather_cache")
        # Upsert records based on date and location
        for record in records:
            coll.update_one(
                {
                    "date": record["date"],
                    "latitude": record["latitude"],
                    "longitude": record["longitude"],
                },
                {"$set": record},
                upsert=True,
            )
        logger.info(f"Successfully cached {len(records)} weather records in MongoDB.")
    except Exception as e:
        logger.error(f"Failed to cache weather data in MongoDB: {e}")


def get_fallback_weather_data(lat: float, lon: float, start_date: str, end_date: str):
    """
    Retrieves weather data from the MongoDB fallback cache if external APIs fail.
    Dates should be in YYYY-MM-DD format.
    """
    try:
        coll = get_sync_collection("weather_cache")
        query = {
            "latitude": lat,
            "longitude": lon,
            "date": {"$gte": start_date, "$lte": end_date},
        }

        cursor = coll.find(query, {"_id": 0}).sort("date", 1)
        records = list(cursor)

        if records:
            logger.info(
                f"Retrieved {len(records)} fallback weather records from MongoDB."
            )
        else:
            logger.warning(
                "No fallback weather records found in MongoDB for the given date range."
            )

        return records
    except Exception as e:
        logger.error(f"Failed to retrieve fallback weather data from MongoDB: {e}")
        return []


def get_fallback_market_prices():
    """
    Retrieves the most recent market prices from cache if Agmarknet fails.
    """
    try:
        coll = get_sync_collection("market_prices")
        # Just return the current records. If empty, ML pipeline will have to handle it.
        count = coll.count_documents({})
        if count > 0:
            logger.info(f"Retrieved {count} cached market price records.")
            return list(coll.find({}, {"_id": 0}))
        else:
            logger.warning("MongoDB market_prices cache is completely empty.")
            return []
    except Exception as e:
        logger.error(f"Failed to retrieve fallback market prices: {e}")
        return []
