"""
KisanMitra AI — Phase 8: End-to-End Validation
Tests:
  1. Prediction API for trained markets (Tier 1 responses)
  2. Frontend response shape compatibility
  3. Model manager cache stats
  4. Generates a final Stage 1 validation report
"""
import sys
import os
import json
import time
import asyncio
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from database import get_sync_collection
from ensemble.model_manager import model_manager
from ensemble.ensemble import generate_forecast
import pandas as pd
import numpy as np


REPORT_DIR = os.path.join(BACKEND_DIR, "data", "processed")
os.makedirs(REPORT_DIR, exist_ok=True)
REPORT_PATH = os.path.join(REPORT_DIR, "stage1_validation_report.json")


def find_trained_markets(limit_per_commodity: int = 3) -> list[dict]:
    """Discover commodity+market combos that have per-market models on disk."""
    models_dir = model_manager.MODELS_DIR
    trained = {}

    for filename in os.listdir(models_dir):
        if not filename.startswith("sarima_") or not filename.endswith(".pkl"):
            continue
        key = filename.replace("sarima_", "").replace(".pkl", "")
        # Per-market keys contain an underscore separating commodity from market
        # Legacy keys are just the commodity name
        parts = key.split("_", 1)
        if len(parts) == 2:
            commodity, market_key = parts
            # Verify all 3 models exist
            has_xgb = os.path.exists(os.path.join(models_dir, f"xgboost_{key}.pkl"))
            has_lstm = os.path.exists(os.path.join(models_dir, f"lstm_{key}.pkl"))
            has_scaler = os.path.exists(os.path.join(models_dir, f"scaler_{key}.pkl"))
            if has_xgb and has_lstm and has_scaler:
                trained.setdefault(commodity, []).append({
                    "key": key,
                    "commodity": commodity,
                    "market_key": market_key,
                    "market_name": market_key.replace("_", " "),
                })

    # Take a sample per commodity
    result = []
    for commodity, markets in sorted(trained.items()):
        for m in markets[:limit_per_commodity]:
            result.append(m)
    return result


def test_model_loading(commodity: str, market: str) -> dict:
    """Test that model_manager can load models for a commodity+market."""
    start = time.time()
    sarima, xgb_model, lstm, scaler = model_manager.get_models(commodity, market=market)
    load_time = round(time.time() - start, 3)

    return {
        "sarima_loaded": sarima is not None,
        "xgboost_loaded": xgb_model is not None,
        "lstm_loaded": lstm is not None,
        "scaler_loaded": scaler is not None,
        "load_time_s": load_time,
        "all_loaded": all([sarima, xgb_model, lstm, scaler]),
    }


def test_prediction(commodity: str, market: str) -> dict:
    """Run an end-to-end ensemble prediction and verify the response shape."""
    # Load historical data from MongoDB
    collection = get_sync_collection("market_prices")
    query = {"commodity": commodity.lower().strip()}
    if market:
        import re
        market_pattern = re.escape(market.strip())
        query["market"] = {"$regex": f"^{market_pattern}$", "$options": "i"}

    docs = list(collection.find(query, {"_id": 0, "date": 1, "price": 1}).sort("date", 1))

    if len(docs) < 30:
        return {"status": "SKIP", "reason": f"Only {len(docs)} records in DB", "tier": None}

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Build features (simplified — same as predict.py)
    prices = df["price"].tolist()
    latest = df.iloc[-1].to_dict()
    latest["price_lag_7"] = df["price"].shift(7).iloc[-1]
    latest["price_lag_14"] = df["price"].shift(14).iloc[-1]
    latest["price_lag_30"] = df["price"].shift(30).iloc[-1]
    latest["rolling_mean_7"] = df["price"].rolling(7).mean().iloc[-1]
    latest["rolling_mean_30"] = df["price"].rolling(30).mean().iloc[-1]
    latest["rolling_std_7"] = df["price"].rolling(7).std().iloc[-1]
    exp1 = df["price"].ewm(span=12, adjust=False).mean()
    exp2 = df["price"].ewm(span=26, adjust=False).mean()
    latest["macd"] = (exp1 - exp2).iloc[-1]
    latest["macd_signal"] = (exp1 - exp2).ewm(span=9, adjust=False).mean().iloc[-1]
    rm30 = df["price"].rolling(30).mean()
    rs30 = df["price"].rolling(30).std()
    latest["bollinger_high"] = (rm30 + rs30 * 2).iloc[-1]
    latest["bollinger_low"] = (rm30 - rs30 * 2).iloc[-1]
    latest["day_of_week"] = df["date"].dt.dayofweek.iloc[-1]
    latest["month"] = df["date"].dt.month.iloc[-1]
    latest["temperature"] = 25.0
    latest["rainfall"] = 2.0

    start = time.time()
    result = generate_forecast(
        commodity=commodity,
        mandi=market,
        horizon=7,
        latest_features=latest,
        historical_prices_30d=prices,
        run_models=["SARIMA", "XGBoost", "LSTM"],
    )
    pred_time = round(time.time() - start, 3)

    if result is None:
        return {"status": "FAIL", "reason": "generate_forecast returned None", "tier": None}

    # Verify response shape (frontend compatibility)
    required_keys = ["commodity", "mandi", "horizon", "forecast", "prediction_source"]
    missing_keys = [k for k in required_keys if k not in result]

    forecast_valid = True
    if result.get("forecast"):
        for entry in result["forecast"]:
            if not all(k in entry for k in ["date", "price", "lower", "upper"]):
                forecast_valid = False
                break

    tier = 1 if result.get("prediction_source") == "ensemble" else 2

    return {
        "status": "PASS" if not missing_keys and forecast_valid else "FAIL",
        "tier": tier,
        "prediction_source": result.get("prediction_source"),
        "active_models": result.get("active_models", []),
        "model_weights": result.get("model_weights", {}),
        "forecast_days": len(result.get("forecast", [])),
        "sample_price": result["forecast"][0]["price"] if result.get("forecast") else None,
        "confidence": result.get("confidence"),
        "missing_keys": missing_keys,
        "forecast_shape_valid": forecast_valid,
        "prediction_time_s": pred_time,
        "data_records": len(docs),
    }


def run_validation():
    print("=" * 65)
    print("KisanMitra AI -- Phase 8: End-to-End Validation")
    print("=" * 65)

    # Refresh model index to pick up newly trained models
    model_manager.refresh_index()
    cache_stats = model_manager.get_cache_stats()
    print(f"\nModel Manager: {cache_stats['available_keys']} available keys, "
          f"{cache_stats['cached_keys']} cached")

    # Find trained per-market models
    trained = find_trained_markets(limit_per_commodity=3)
    print(f"\nFound {len(trained)} per-market trained model sets to validate")

    if not trained:
        print("\n[WARNING] No per-market models found! Stage 1 training may not have run yet.")
        print("   Falling back to legacy commodity-level model validation.")
        # Validate legacy models instead
        legacy_commodities = ["onion", "potato", "tomato"]
        trained = [{"commodity": c, "market_key": "", "market_name": "", "key": c} for c in legacy_commodities]

    results = []
    pass_count = 0
    fail_count = 0
    tier1_count = 0

    for i, target in enumerate(trained, 1):
        commodity = target["commodity"]
        market = target["market_name"]
        key = target["key"]

        print(f"\n[{i}/{len(trained)}] Testing: {commodity} / {market or '(legacy)'} [key={key}]")

        # Test 1: Model loading
        load_result = test_model_loading(commodity, market)
        status_emoji = "OK" if load_result["all_loaded"] else "WARN"
        print(f"  Model Load: {status_emoji}  (S={load_result['sarima_loaded']} "
              f"X={load_result['xgboost_loaded']} L={load_result['lstm_loaded']} "
              f"| {load_result['load_time_s']}s)")

        # Test 2: End-to-end prediction
        pred_result = test_prediction(commodity, market)
        if pred_result["status"] == "PASS":
            pass_count += 1
            if pred_result["tier"] == 1:
                tier1_count += 1
            print(f"  Prediction: [PASS] Tier {pred_result['tier']} | "
                  f"Models: {pred_result['active_models']} | "
                  f"Price: Rs.{pred_result['sample_price']} | "
                  f"{pred_result['prediction_time_s']}s")
        elif pred_result["status"] == "SKIP":
            print(f"  Prediction: [SKIP] {pred_result['reason']}")
        else:
            fail_count += 1
            print(f"  Prediction: [FAIL] {pred_result.get('reason', 'Unknown failure')}")

        results.append({
            "commodity": commodity,
            "market": market,
            "key": key,
            "model_loading": load_result,
            "prediction": pred_result,
        })

    # Final cache stats
    final_cache = model_manager.get_cache_stats()

    # Build report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "phase": "Stage 1 End-to-End Validation",
        "total_tested": len(results),
        "passed": pass_count,
        "failed": fail_count,
        "tier1_count": tier1_count,
        "cache_stats": final_cache,
        "results": results,
        "overall_status": "PASS" if fail_count == 0 and pass_count > 0 else "PARTIAL" if pass_count > 0 else "FAIL",
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'=' * 65}")
    print(f"VALIDATION SUMMARY")
    print(f"{'=' * 65}")
    print(f"  Tested : {len(results)}")
    print(f"  Passed : {pass_count}  (Tier 1: {tier1_count})")
    print(f"  Failed : {fail_count}")
    print(f"  Status : {report['overall_status']}")
    print(f"  Cache  : {final_cache['hits']} hits / {final_cache['misses']} misses / {final_cache['evictions']} evictions")
    print(f"  Report : {REPORT_PATH}")
    print(f"{'=' * 65}")

    return report


if __name__ == "__main__":
    run_validation()
