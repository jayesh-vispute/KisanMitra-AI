"""
KisanMitra AI — Fast Historical Dataset Import
Optimized for speed: drops existing historical data and bulk-inserts.
"""
import pandas as pd
import numpy as np
import os
import sys
import time
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from database import get_sync_collection
import pymongo

CSV_PATH = os.path.abspath(os.path.join(BACKEND_DIR, "..", "data", "Agriculture_price_dataset.csv"))
BATCH_SIZE = 10000

def main():
    start_all = time.time()
    print("=" * 60)
    print("KisanMitra AI — Fast Historical Import")
    print("=" * 60)

    # 1. Load & clean
    print("\n[1/4] Loading CSV...")
    t0 = time.time()
    df = pd.read_csv(CSV_PATH)
    print(f"  Loaded {len(df)} rows in {time.time()-t0:.1f}s")

    # Rename
    df = df.rename(columns={
        "STATE": "state", "District Name": "district", "Market Name": "market",
        "Commodity": "commodity", "Variety": "variety", "Grade": "grade",
        "Min_Price": "min_price", "Max_Price": "max_price",
        "Modal_Price": "price", "Price Date": "date",
    })

    # Normalize
    df["state"] = df["state"].str.strip().str.title()
    df["district"] = df["district"].str.strip().str.title()
    df["market"] = df["market"].str.strip().str.title()
    df["commodity"] = df["commodity"].str.strip().str.lower()

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], format="mixed", dayfirst=True, errors="coerce")
    before = len(df)
    df = df.dropna(subset=["date"])

    # Validate prices
    for col in ["price", "min_price", "max_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] > 0]

    # Remove impossible price relationships
    df = df[~((df["min_price"] > df["price"]) | (df["price"] > df["max_price"]))]

    # Dedup
    df = df.drop_duplicates(subset=["commodity", "market", "date", "price"])

    # Add metadata
    df["data_type"] = "historical_csv"

    print(f"  Cleaned: {before} -> {len(df)} rows")
    print(f"  Commodities: {sorted(df['commodity'].unique())}")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    # 2. Clear old historical data only (preserve live/API data)
    print("\n[2/4] Preparing MongoDB...")
    collection = get_sync_collection("market_prices")
    
    deleted = collection.delete_many({"data_type": "historical_csv"})
    print(f"  Cleared {deleted.deleted_count} old historical_csv records")

    # 3. Bulk insert
    print("\n[3/4] Inserting records...")
    records = df.to_dict("records")
    total = len(records)
    inserted = 0
    t0 = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        try:
            result = collection.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
        except pymongo.errors.BulkWriteError as bwe:
            inserted += bwe.details.get("nInserted", 0)
        
        progress = min(i + BATCH_SIZE, total)
        elapsed = time.time() - t0
        rate = progress / elapsed if elapsed > 0 else 0
        print(f"  {progress:>7}/{total} ({progress*100/total:.0f}%) | {rate:.0f} rec/s", end="\r")

    insert_time = time.time() - t0
    print(f"\n  Inserted {inserted} records in {insert_time:.1f}s")

    # 4. Create indexes
    print("\n[4/4] Creating indexes...")
    collection.create_index([("commodity", 1), ("market", 1), ("date", 1)], name="comm_market_date", background=True)
    collection.create_index([("commodity", 1)], name="commodity_idx", background=True)
    collection.create_index([("market", 1)], name="market_idx", background=True)
    collection.create_index([("date", 1)], name="date_idx", background=True)
    print("  Indexes created.")

    # Validation summary
    total_docs = collection.count_documents({})
    pipeline = [
        {"$group": {"_id": "$commodity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    per_commodity = {r["_id"]: r["count"] for r in collection.aggregate(pipeline)}

    # Eligible series
    series_pipeline = [
        {"$group": {"_id": {"c": "$commodity", "m": "$market"}, "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 40}}},
        {"$count": "eligible"}
    ]
    eligible_result = list(collection.aggregate(series_pipeline))
    eligible = eligible_result[0]["eligible"] if eligible_result else 0

    elapsed_total = time.time() - start_all

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "duration_s": round(elapsed_total, 1),
        "rows_cleaned": len(df),
        "rows_inserted": inserted,
        "total_in_db": total_docs,
        "per_commodity": per_commodity,
        "eligible_series": eligible,
    }
    
    report_path = os.path.join(BACKEND_DIR, "data", "processed", "import_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE in {elapsed_total:.1f}s")
    print(f"{'='*60}")
    print(f"  Total in DB: {total_docs}")
    for c, n in sorted(per_commodity.items()):
        print(f"    {c:15s}: {n:>8,}")
    print(f"  Eligible series (>=40 records): {eligible}")
    print(f"  Report: {report_path}")

if __name__ == "__main__":
    main()
