"""
KisanMitra AI — In-Memory TTL Cache
Thread-safe cache with configurable expiry for API response caching.
"""

import time
import threading
import logging

logger = logging.getLogger("KisanMitra.Cache")


class TTLCache:
    """Simple thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = 900):
        """
        Args:
            default_ttl: Default time-to-live in seconds (default: 900 = 15 minutes).
        """
        self._store: dict = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        self._stats = {"hits": 0, "misses": 0}

    def get(self, key: str):
        """
        Retrieve a cached value. Returns None if key is missing or expired.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            value, expiry = entry
            if time.time() > expiry:
                del self._store[key]
                self._stats["misses"] += 1
                logger.debug(f"Cache EXPIRED: {key}")
                return None

            self._stats["hits"] += 1
            logger.debug(f"Cache HIT: {key}")
            return value

    def set(self, key: str, value, ttl_seconds: int = None):
        """
        Store a value with a TTL. Uses default_ttl if ttl_seconds is None.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl
        with self._lock:
            self._store[key] = (value, expiry)
        logger.debug(f"Cache SET: {key} (TTL={ttl}s)")

    def invalidate(self, key: str):
        """Remove a specific key from cache."""
        with self._lock:
            self._store.pop(key, None)
        logger.debug(f"Cache INVALIDATE: {key}")

    def invalidate_prefix(self, prefix: str):
        """Remove all keys that start with the given prefix."""
        with self._lock:
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
        logger.debug(f"Cache INVALIDATE_PREFIX: {prefix} ({len(keys_to_remove)} keys)")

    def clear(self):
        """Clear the entire cache."""
        with self._lock:
            self._store.clear()
        logger.debug("Cache CLEARED")

    @property
    def stats(self):
        """Return cache hit/miss statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                round(self._stats["hits"] / total * 100, 1) if total > 0 else 0
            )
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "total": total,
                "hit_rate_pct": hit_rate,
                "entries": len(self._store),
            }


# ---------------------------------------------------------------------------
# Shared cache instances used across the application
# ---------------------------------------------------------------------------

# Market metadata cache (states, districts, mandis) — 30 minute TTL
metadata_cache = TTLCache(default_ttl=1800)

# Price data cache — 15 minute TTL
price_cache = TTLCache(default_ttl=900)

# API response cache — 15 minute TTL
api_cache = TTLCache(default_ttl=900)
