"""
database.py — Async MongoDB connection using motor, with sync pymongo fallback.
"""
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "kisanmitra"

# Module-level state
_async_client: AsyncIOMotorClient | None = None
_sync_client: pymongo.MongoClient | None = None


async def connect_db():
    """Connect to MongoDB on application startup."""
    global _async_client
    try:
        _async_client = AsyncIOMotorClient(MONGO_URI)
        # Ping to verify the connection is alive
        await _async_client.admin.command("ping")
        print(f"[database] Connected to MongoDB at {MONGO_URI}")
    except Exception as e:
        print(f"[database] MongoDB connection error: {e}")
        _async_client = None


async def close_db():
    """Close MongoDB connections on application shutdown."""
    global _async_client, _sync_client
    if _async_client:
        _async_client.close()
        _async_client = None
        print("[database] Async MongoDB connection closed.")
    if _sync_client:
        _sync_client.close()
        _sync_client = None
        print("[database] Sync MongoDB connection closed.")


def get_database():
    """Return the async database instance."""
    if _async_client is None:
        raise RuntimeError("[database] Async client not connected. Call connect_db() first.")
    return _async_client[DB_NAME]


def get_async_collection(name: str):
    """Return an async collection by name."""
    db = get_database()
    return db[name]


def get_sync_collection(name: str):
    """Return a sync pymongo collection by name."""
    global _sync_client
    if _sync_client is None:
        _sync_client = pymongo.MongoClient(MONGO_URI)
    return _sync_client[DB_NAME][name]
