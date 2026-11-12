"""
KisanMitra AI — Per-Market Model Training (Stage 1 & 2)
Trains SARIMA, XGBoost, and Neural-Net (MLPRegressor) per commodity+market combination.

Usage:
    python train_per_market.py                    # Stage 1: Top 50 markets per commodity
    python train_per_market.py --stage 2          # Stage 2: All eligible markets
    python train_per_market.py --resume           # Resume interrupted training
    python train_per_market.py --commodity onion   # Train only one commodity
"""

import pandas as pd
import numpy as np
import os
import sys
import json
import time
import argparse
import joblib
from datetime import datetime
from statsmodels.tsa.statespace.sarimax import SARIMAX
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from database import get_sync_collection

np.random.seed(42)

MODELS_DIR = os.path.join(BACKEND_DIR, "models", "saved")
CHECKPOINT_PATH = os.path.join(BACKEND_DIR, "data", "processed", "training_checkpoint.json")
REPORT_PATH = os.path.join(BACKEND_DIR, "data", "processed", "training_report.json")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)

MIN_HISTORY = 40   # Minimum records to train any model
SEQ_LEN = 30       # Sequence length for neural network
TOP_N_STAGE1 = 50  # Markets per commodity in Stage 1

FEATURES = [
    "price_lag_7", "price_lag_14", "price_lag_30", "rolling_mean_7",
    "rolling_mean_30", "rolling_std_7", "macd", "macd_signal",
    "bollinger_high", "bollinger_low", "day_of_week", "month",
    "temperature", "rainfall",
]


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def sanitize_key(commodity: str, market: str) -> str:
    """Create a filesystem-safe model key."""
    return f"{commodity.lower().strip()}_{market.strip().replace(' ', '_')}"


def create_features(group: pd.DataFrame) -> pd.DataFrame:
    """Generate ML features for a single market time series."""
    g = group.copy()
    g = g.sort_values("date").reset_index(drop=True)
    
    g["price_lag_7"] = g["price"].shift(7)
    g["price_lag_14"] = g["price"].shift(14)
    g["price_lag_30"] = g["price"].shift(30)
    g["rolling_mean_7"] = g["price"].rolling(window=7).mean()
    g["rolling_mean_30"] = g["price"].rolling(window=30).mean()
    g["rolling_std_7"] = g["price"].rolling(window=7).std().fillna(0)
    
    exp1 = g["price"].ewm(span=12, adjust=False).mean()
    exp2 = g["price"].ewm(span=26, adjust=False).mean()
    g["macd"] = exp1 - exp2
    g["macd_signal"] = g["macd"].ewm(span=9, adjust=False).mean()
    
    g["bollinger_high"] = g["rolling_mean_30"] + (g["price"].rolling(window=30).std() * 2)
    g["bollinger_low"] = g["rolling_mean_30"] - (g["price"].rolling(window=30).std() * 2)
    
    g["day_of_week"] = g["date"].dt.dayofweek
    g["month"] = g["date"].dt.month
    
    # Synthetic weather features (seasonal heuristic)
    g["temperature"] = 25 + 10 * np.sin(g["date"].dt.dayofyear / 365.0 * 2 * np.pi)
    g["rainfall"] = np.where(g["month"].isin([6, 7, 8, 9]), 5.0, 0.5)
    
    return g


def create_sequences(data, seq_length=SEQ_LEN):
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        xs.append(data[i:(i + seq_length)].flatten())
        ys.append(data[i + seq_length][0])
    return np.array(xs), np.array(ys)


def load_checkpoint() -> set:
    """Load previously trained keys from checkpoint file."""
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r") as f:
            data = json.load(f)
        return set(data.get("completed_keys", []))
    return set()


def save_checkpoint(completed_keys: set):
    """Save training progress."""
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump({
            "completed_keys": list(completed_keys),
            "last_updated": datetime.utcnow().isoformat(),
        }, f, indent=2)


# ---------------------------------------------------------------------------
# TRAINING FUNCTIONS
# ---------------------------------------------------------------------------
def train_sarima(ts: pd.Series, key: str) -> dict | None:
    """Train SARIMA on a single time series. Returns metrics or None."""
    if len(ts) < MIN_HISTORY:
        return None
    try:
        train, test = ts.iloc[:-30], ts.iloc[-30:]
        if len(test) == 0:
            test = ts.iloc[-10:]
            train = ts.iloc[:-10]
        
        model = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12))
        result = model.fit(disp=False, maxiter=200)
        
        save_path = os.path.join(MODELS_DIR, f"sarima_{key}.pkl")
        joblib.dump(result, save_path)
        
        pred = result.get_forecast(steps=len(test)).predicted_mean.values
        mae_val = mean_absolute_error(test.values, pred)
        rmse_val = float(np.sqrt(mean_squared_error(test.values, pred)))
        mape_val = mape(test.values, pred)
        
        return {"MAE": round(mae_val, 2), "RMSE": round(rmse_val, 2), "MAPE": round(mape_val * 100, 2)}
    except Exception as e:
        print(f"    [SARIMA] Failed for {key}: {e}")
        return None


def train_xgboost(df: pd.DataFrame, key: str) -> dict | None:
    """Train XGBoost on feature-engineered data. Returns metrics or None."""
    available_features = [f for f in FEATURES if f in df.columns]
    if len(df) < MIN_HISTORY or len(available_features) < 5:
        return None
    try:
        data = df.dropna(subset=available_features + ["price"])
        if len(data) < MIN_HISTORY:
            return None
        
        X, y = data[available_features], data["price"]
        split = int(len(data) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        
        if len(X_test) == 0:
            return None
        
        from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
        tscv = TimeSeriesSplit(n_splits=min(3, max(2, len(X_train) // 30)))
        xgb_base = xgb.XGBRegressor(random_state=42)
        param_search = {
            "n_estimators": [200, 500],
            "learning_rate": [0.01, 0.05, 0.1],
            "max_depth": [4, 6],
        }
        search = RandomizedSearchCV(
            xgb_base, param_distributions=param_search, n_iter=5,
            cv=tscv, scoring="neg_mean_absolute_error", random_state=42,
        )
        search.fit(X_train, y_train)
        model = search.best_estimator_
        
        save_path = os.path.join(MODELS_DIR, f"xgboost_{key}.pkl")
        joblib.dump(model, save_path)
        
        pred = model.predict(X_test)
        mae_val = mean_absolute_error(y_test, pred)
        rmse_val = float(np.sqrt(mean_squared_error(y_test, pred)))
        mape_val = mape(y_test.values, pred)
        
        return {
            "MAE": round(mae_val, 2), "RMSE": round(rmse_val, 2), "MAPE": round(mape_val * 100, 2),
            "best_params": search.best_params_,
        }
    except Exception as e:
        print(f"    [XGBoost] Failed for {key}: {e}")
        return None


def train_lstm(df: pd.DataFrame, key: str) -> dict | None:
    """Train MLPRegressor (neural net) on price sequences. Returns metrics or None."""
    data = df.sort_values("date")
    prices = data["price"].values.reshape(-1, 1)
    if len(prices) < MIN_HISTORY:
        return None
    try:
        scaler = MinMaxScaler()
        data_scaled = scaler.fit_transform(prices)
        
        scaler_path = os.path.join(MODELS_DIR, f"scaler_{key}.pkl")
        joblib.dump(scaler, scaler_path)
        
        X, y = create_sequences(data_scaled)
        if len(X) < 10:
            return None
        
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        if len(X_test) == 0:
            return None
        
        nn = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32), max_iter=500,
            early_stopping=True, random_state=42, activation="relu",
            solver="adam", learning_rate="adaptive",
            validation_fraction=0.15, n_iter_no_change=20,
        )
        nn.fit(X_train, y_train)
        
        save_path = os.path.join(MODELS_DIR, f"lstm_{key}.pkl")
        joblib.dump(nn, save_path)
        
        pred_scaled = nn.predict(X_test).reshape(-1, 1)
        pred_prices = scaler.inverse_transform(pred_scaled).flatten()
        true_prices = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
        
        mae_val = mean_absolute_error(true_prices, pred_prices)
        rmse_val = float(np.sqrt(mean_squared_error(true_prices, pred_prices)))
        mape_val = mape(true_prices, pred_prices)
        
        return {"MAE": round(mae_val, 2), "RMSE": round(rmse_val, 2), "MAPE": round(mape_val * 100, 2)}
    except Exception as e:
        print(f"    [LSTM] Failed for {key}: {e}")
        return None


# ---------------------------------------------------------------------------
# ENSEMBLE WEIGHTS
# ---------------------------------------------------------------------------
def compute_and_save_weights(key: str, commodity: str, market: str, metrics: dict):
    """Compute dynamic inverse-MSE weights and save to MongoDB."""
    db_weights = get_sync_collection("ensemble_weights")
    
    sarima_rmse = metrics.get("SARIMA", {}).get("RMSE", 1e6)
    xgb_rmse = metrics.get("XGBoost", {}).get("RMSE", 1e6)
    lstm_rmse = metrics.get("LSTM", {}).get("RMSE", 1e6)
    
    inv_sarima = 1.0 / (sarima_rmse**2 + 1e-6)
    inv_xgb = 1.0 / (xgb_rmse**2 + 1e-6)
    inv_lstm = 1.0 / (lstm_rmse**2 + 1e-6)
    total = inv_sarima + inv_xgb + inv_lstm
    
    w = {"SARIMA": inv_sarima / total, "XGBoost": inv_xgb / total, "LSTM": inv_lstm / total}
    
    try:
        # Save with both commodity and market-specific keys
        db_weights.update_one(
            {"commodity": commodity, "market": market},
            {"$set": {**w, "key": key, "updated_at": datetime.utcnow().isoformat()}},
            upsert=True,
        )
        # Also save commodity-level fallback weights
        db_weights.update_one(
            {"commodity": commodity, "market": {"$exists": False}},
            {"$set": {**w, "updated_at": datetime.utcnow().isoformat()}},
            upsert=True,
        )
    except Exception as e:
        print(f"    [Warning] Failed to save ensemble weights to DB: {e}")
    return w


# ---------------------------------------------------------------------------
# MAIN TRAINING LOOP
# ---------------------------------------------------------------------------
def run_training(stage: int = 1, resume: bool = False, filter_commodity: str = None):
    """Execute the training pipeline."""
    global_start = time.time()
    print("=" * 60)
    print(f"KisanMitra AI — Per-Market Training (Stage {stage})")
    print("=" * 60)
    
    # Load data from MongoDB
    collection = get_sync_collection("market_prices")
    
    # Build the list of eligible commodity+market combos
    pipeline = [
        {"$group": {
            "_id": {"commodity": "$commodity", "market": "$market"},
            "count": {"$sum": 1},
        }},
        {"$match": {"count": {"$gte": MIN_HISTORY}}},
        {"$sort": {"count": -1}},
    ]
    
    combos = list(collection.aggregate(pipeline))
    print(f"  > Found {len(combos)} eligible commodity+market combinations (>= {MIN_HISTORY} records)")
    
    # Group by commodity
    by_commodity = {}
    for c in combos:
        comm = c["_id"]["commodity"]
        market = c["_id"]["market"]
        count = c["count"]
        by_commodity.setdefault(comm, []).append((market, count))
    
    if filter_commodity:
        filter_commodity = filter_commodity.lower().strip()
        by_commodity = {k: v for k, v in by_commodity.items() if k == filter_commodity}
    
    # Select targets based on stage
    targets = []
    for commodity, markets in sorted(by_commodity.items()):
        if stage == 1:
            selected = markets[:TOP_N_STAGE1]
        else:
            selected = markets
        for market, count in selected:
            targets.append((commodity, market, count))
    
    print(f"  > Training targets: {len(targets)} combinations across {len(by_commodity)} commodities")
    
    # Checkpoint support
    completed_keys = load_checkpoint() if resume else set()
    if resume and completed_keys:
        print(f"  > Resuming: {len(completed_keys)} already completed")
    
    # Load weather cache
    weather_df = pd.DataFrame()
    try:
        db_weather = get_sync_collection("weather_cache")
        weather_list = list(db_weather.find({}, {"_id": 0}))
        if weather_list:
            weather_df = pd.DataFrame(weather_list)
            weather_df["date"] = pd.to_datetime(weather_df["date"])
            weather_df = weather_df.groupby("date")[["temperature", "rainfall"]].mean().reset_index()
            print(f"  > Loaded {len(weather_df)} weather cache records")
    except Exception as e:
        print(f"  > Weather cache unavailable: {e}")
    
    all_metrics = {}
    trained_count = 0
    skipped_count = 0
    failed_count = 0
    
    for idx, (commodity, market, count) in enumerate(targets, 1):
        key = sanitize_key(commodity, market)
        
        if key in completed_keys:
            skipped_count += 1
            continue
        
        print(f"\n[{idx}/{len(targets)}] Training: {commodity} / {market} ({count} records)")
        
        # Fetch data for this specific commodity+market
        query = {"commodity": commodity, "market": market}
        docs = list(collection.find(query, {"_id": 0}).sort("date", 1))
        df = pd.DataFrame(docs)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        if len(df) < MIN_HISTORY:
            print(f"  Skipping (only {len(df)} records)")
            skipped_count += 1
            continue
        
        # Feature engineering
        df_feat = create_features(df)
        
        # Merge weather data if available
        if not weather_df.empty:
            df_feat = pd.merge(df_feat, weather_df, on="date", how="left", suffixes=("_drop", ""))
            for col in ["temperature", "rainfall"]:
                if f"{col}_drop" in df_feat.columns:
                    df_feat[col] = df_feat[col].fillna(df_feat[f"{col}_drop"])
                    df_feat = df_feat.drop(columns=[f"{col}_drop"])
                df_feat[col] = df_feat[col].ffill().bfill()
        
        metrics = {}
        
        # Train SARIMA
        ts = df_feat.set_index("date")["price"]
        sarima_metrics = train_sarima(ts, key)
        if sarima_metrics:
            metrics["SARIMA"] = sarima_metrics
            print(f"    SARIMA  -> MAE={sarima_metrics['MAE']:.2f}  MAPE={sarima_metrics['MAPE']:.2f}%")
        
        # Train XGBoost
        xgb_metrics = train_xgboost(df_feat, key)
        if xgb_metrics:
            metrics["XGBoost"] = xgb_metrics
            print(f"    XGBoost -> MAE={xgb_metrics['MAE']:.2f}  MAPE={xgb_metrics['MAPE']:.2f}%")
        
        # Train LSTM
        lstm_metrics = train_lstm(df_feat, key)
        if lstm_metrics:
            metrics["LSTM"] = lstm_metrics
            print(f"    LSTM    -> MAE={lstm_metrics['MAE']:.2f}  MAPE={lstm_metrics['MAPE']:.2f}%")
        
        if metrics:
            # Compute ensemble weights
            if len(metrics) == 3:
                weights = compute_and_save_weights(key, commodity, market, metrics)
                print(f"    Weights -> S={weights['SARIMA']:.3f}  X={weights['XGBoost']:.3f}  L={weights['LSTM']:.3f}")
            
            all_metrics[key] = {
                "commodity": commodity,
                "market": market,
                "record_count": count,
                "models": metrics,
                "trained_at": datetime.utcnow().isoformat(),
            }
            trained_count += 1
        else:
            failed_count += 1
        
        # Checkpoint after every market
        completed_keys.add(key)
        save_checkpoint(completed_keys)
    
    # Save metrics to MongoDB
    try:
        db_metrics = get_sync_collection("model_metrics")
        db_metrics.update_one(
            {"type": "per_market_metrics"},
            {"$set": {"data": all_metrics, "updated_at": datetime.utcnow().isoformat()}},
            upsert=True,
        )
    except Exception as e:
        print(f"    [Warning] Failed to save model metrics to DB: {e}")
    
    elapsed = time.time() - global_start
    
    # Generate report
    report = {
        "stage": stage,
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": round(elapsed, 1),
        "duration_human": f"{int(elapsed//3600)}h {int((elapsed%3600)//60)}m {int(elapsed%60)}s",
        "total_targets": len(targets),
        "trained": trained_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "commodities": list(by_commodity.keys()),
        "metrics_summary": {},
    }
    
    # Aggregate metrics
    for key, data in all_metrics.items():
        comm = data["commodity"]
        report["metrics_summary"].setdefault(comm, {"count": 0, "avg_mape": []})
        report["metrics_summary"][comm]["count"] += 1
        for model_name, m in data["models"].items():
            report["metrics_summary"][comm]["avg_mape"].append(m.get("MAPE", 0))
    
    for comm in report["metrics_summary"]:
        mapes = report["metrics_summary"][comm]["avg_mape"]
        report["metrics_summary"][comm]["avg_mape"] = round(np.mean(mapes), 2) if mapes else 0
    
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print(f"TRAINING COMPLETE — Stage {stage}")
    print("=" * 60)
    print(f"  Duration: {report['duration_human']}")
    print(f"  Trained:  {trained_count} | Skipped: {skipped_count} | Failed: {failed_count}")
    print(f"  Report:   {REPORT_PATH}")
    print("=" * 60)
    
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KisanMitra AI Per-Market Model Training")
    parser.add_argument("--stage", type=int, default=1, choices=[1, 2], help="Training stage (1=Top 50, 2=All)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--commodity", type=str, default=None, help="Train only one commodity")
    args = parser.parse_args()
    
    run_training(stage=args.stage, resume=args.resume, filter_commodity=args.commodity)
