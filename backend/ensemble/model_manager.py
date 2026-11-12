"""
KisanMitra AI — Model Manager (LRU Cache Architecture)
Lazily loads per-market ML models on demand with LRU eviction.
Thread-safe for concurrent FastAPI requests.
"""
import joblib
import os
import time
import psutil
from threading import Lock
from collections import OrderedDict
import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger("ModelManager")


class ModelManager:
    """
    Centralized Model Manager with lazy LRU loading.
    
    Instead of loading all models at startup (which doesn't scale to thousands
    of per-market models), this loads models on-demand and keeps the N most
    recently used model sets in an LRU cache.
    
    Model key format: "{commodity}" (legacy) or "{commodity}_{market}" (per-market).
    The manager tries per-market models first, then falls back to commodity-level models.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ModelManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_cache_size: int = 150):
        if not self._initialized:
            self.MODELS_DIR = os.getenv(
                "MODEL_SAVE_PATH",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "saved")),
            )
            self._cache: OrderedDict[str, dict] = OrderedDict()
            self._max_cache_size = max_cache_size
            self._cache_lock = Lock()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0, "load_errors": 0}
            self._available_keys: set[str] = set()
            self._discover_available_models()
            self._initialized = True

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def _discover_available_models(self):
        """Scan the models directory to build an index of available model keys."""
        keys = set()
        if not os.path.exists(self.MODELS_DIR):
            logger.warning(f"Models directory does not exist: {self.MODELS_DIR}")
            return

        for filename in os.listdir(self.MODELS_DIR):
            if not filename.endswith(".pkl"):
                continue
            # Patterns: sarima_onion.pkl, sarima_onion_Lasalgaon.pkl
            for prefix in ("sarima_", "xgboost_", "lstm_", "scaler_"):
                if filename.startswith(prefix):
                    key = filename[len(prefix) :].replace(".pkl", "")
                    keys.add(key)
                    break

        self._available_keys = keys
        logger.info(f"Discovered {len(keys)} unique model keys in {self.MODELS_DIR}")

    def refresh_index(self):
        """Re-scan the models directory (call after training new models)."""
        with self._cache_lock:
            self._discover_available_models()
        logger.info("Model index refreshed.")

    # ------------------------------------------------------------------
    # LRU Cache
    # ------------------------------------------------------------------
    def _load_model_set(self, key: str) -> dict | None:
        """Load SARIMA, XGBoost, LSTM, and scaler for a given key from disk."""
        model_set = {"sarima": None, "xgboost": None, "lstm": None, "scaler": None}
        loaded_any = False
        start = time.time()

        for model_type in ("sarima", "xgboost", "lstm", "scaler"):
            path = os.path.join(self.MODELS_DIR, f"{model_type}_{key}.pkl")
            if os.path.exists(path):
                try:
                    model_set[model_type] = joblib.load(path)
                    loaded_any = True
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")
                    self._stats["load_errors"] += 1

        load_time = time.time() - start
        if loaded_any:
            logger.debug(f"Loaded model set '{key}' from disk in {load_time:.3f}s")
        return model_set if loaded_any else None

    def _evict_oldest(self):
        """Remove the least recently used entry from the cache."""
        if self._cache:
            evicted_key, _ = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
            logger.debug(f"Evicted model set '{evicted_key}' from cache (total evictions: {self._stats['evictions']})")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_models(self, commodity: str, market: str = None):
        """
        Thread-safe model retrieval with LRU caching.
        
        Lookup order:
        1. Per-market key: "{commodity}_{market}" (sanitized)
        2. Commodity-only key: "{commodity}"
        
        Returns (sarima, xgboost, lstm, scaler) — any may be None.
        """
        commodity_clean = commodity.lower().strip()

        # Build candidate keys in priority order
        candidates = []
        if market:
            market_clean = market.strip().replace(" ", "_")
            per_market_key = f"{commodity_clean}_{market_clean}"
            candidates.append(per_market_key)
        candidates.append(commodity_clean)

        with self._cache_lock:
            # Try each candidate
            for key in candidates:
                # Cache hit
                if key in self._cache:
                    self._cache.move_to_end(key)  # Mark as recently used
                    self._stats["hits"] += 1
                    mods = self._cache[key]
                    return mods["sarima"], mods["xgboost"], mods["lstm"], mods["scaler"]

                # Cache miss — try loading from disk
                if key in self._available_keys:
                    self._stats["misses"] += 1
                    model_set = self._load_model_set(key)
                    if model_set:
                        # Evict if at capacity
                        while len(self._cache) >= self._max_cache_size:
                            self._evict_oldest()
                        self._cache[key] = model_set
                        return model_set["sarima"], model_set["xgboost"], model_set["lstm"], model_set["scaler"]

        # Nothing found
        return None, None, None, None

    def preload_models(self, keys: list[str] = None):
        """
        Optionally preload a set of model keys into cache at startup.
        If keys is None, preloads commodity-level (legacy) models.
        """
        if keys is None:
            # Discover legacy commodity-level models (keys without underscores after the commodity)
            legacy_keys = set()
            for k in self._available_keys:
                # Legacy keys are simple: 'onion', 'potato', etc.
                if "_" not in k:
                    legacy_keys.add(k)
            keys = list(legacy_keys)

        logger.info(f"Preloading {len(keys)} model sets...")
        start = time.time()
        for key in keys:
            with self._cache_lock:
                if key not in self._cache and key in self._available_keys:
                    model_set = self._load_model_set(key)
                    if model_set:
                        while len(self._cache) >= self._max_cache_size:
                            self._evict_oldest()
                        self._cache[key] = model_set

        elapsed = time.time() - start
        memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        logger.info(f"Preloaded {len(self._cache)} model sets in {elapsed:.2f}s | Memory: {memory_mb:.0f} MB")

    def get_cache_stats(self) -> dict:
        """Return cache performance statistics."""
        with self._cache_lock:
            return {
                **self._stats,
                "cached_keys": len(self._cache),
                "available_keys": len(self._available_keys),
                "max_cache_size": self._max_cache_size,
                "memory_mb": round(psutil.Process().memory_info().rss / (1024 * 1024), 1),
            }

    def warmup_models(self):
        """Perform lightweight inference to initialize lazy C/C++ backends."""
        logger.info("Warming up cached models...")
        with self._cache_lock:
            for key, mods in self._cache.items():
                if mods["xgboost"]:
                    try:
                        try:
                            xgb_features = mods["xgboost"].feature_names_in_
                        except AttributeError:
                            xgb_features = [
                                "price_lag_7", "price_lag_14", "price_lag_30", "rolling_mean_7",
                                "rolling_mean_30", "rolling_std_7", "macd", "macd_signal",
                                "bollinger_high", "bollinger_low", "day_of_week", "month",
                                "temperature", "rainfall",
                            ]
                        dummy_features = pd.DataFrame([np.zeros(len(xgb_features))], columns=xgb_features)
                        mods["xgboost"].predict(dummy_features)
                    except Exception:
                        pass

                if mods["lstm"] and mods["scaler"]:
                    try:
                        dummy_input = np.zeros((1, 30))
                        mods["lstm"].predict(dummy_input)
                    except Exception:
                        pass
        logger.info("Model warmup complete.")


# Global singleton instance
model_manager = ModelManager()
