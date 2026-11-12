"""
KisanMitra AI — Phase 3 Database Validation
Verifies:
  1. Record counts per commodity
  2. Date ranges per commodity
  3. Market / District / State counts
Outputs a validation_report.json and prints a summary.
"""
import sys
import os
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from database import get_sync_collection


REPORT_DIR = os.path.join(BACKEND_DIR, "data", "processed")
os.makedirs(REPORT_DIR, exist_ok=True)
REPORT_PATH = os.path.join(REPORT_DIR, "validation_report.json")


def run_verification():
    collection = get_sync_collection("market_prices")
    total_count = collection.count_documents({})

    print("=" * 65)
    print("KisanMitra AI — Phase 3: Database Validation")
    print("=" * 65)
    print(f"\nTotal documents in market_prices: {total_count:,}")

    if total_count == 0:
        print("\n[WARNING] Collection is empty -- nothing to validate.")
        return

    # ------------------------------------------------------------------
    # 1. Record counts per commodity
    # ------------------------------------------------------------------
    print("\n--- 1. Record counts per commodity -----------------------------")
    pipeline_counts = [
        {"$group": {"_id": "$commodity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    per_commodity = {r["_id"]: r["count"] for r in collection.aggregate(pipeline_counts)}
    for commodity, count in per_commodity.items():
        print(f"  {commodity:20s}: {count:>10,}")

    # ------------------------------------------------------------------
    # 2. Date ranges per commodity
    # ------------------------------------------------------------------
    print("\n--- 2. Date ranges per commodity -------------------------------")
    pipeline_dates = [
        {"$group": {
            "_id": "$commodity",
            "min_date": {"$min": "$date"},
            "max_date": {"$max": "$date"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    date_ranges = {}
    for r in collection.aggregate(pipeline_dates):
        commodity = r["_id"]
        min_d = r["min_date"]
        max_d = r["max_date"]
        # Convert to string safely
        min_str = min_d.strftime("%Y-%m-%d") if hasattr(min_d, "strftime") else str(min_d)[:10]
        max_str = max_d.strftime("%Y-%m-%d") if hasattr(max_d, "strftime") else str(max_d)[:10]
        date_ranges[commodity] = {"min": min_str, "max": max_str, "records": r["count"]}
        print(f"  {commodity:20s}: {min_str}  ->  {max_str}  ({r['count']:,} records)")

    # ------------------------------------------------------------------
    # 3. Market / District / State counts
    # ------------------------------------------------------------------
    print("\n--- 3. Market / District / State unique counts -----------------")
    unique_markets = collection.distinct("market")
    unique_districts = collection.distinct("district")
    unique_states = collection.distinct("state")

    geo_summary = {
        "unique_markets": len(unique_markets),
        "unique_districts": len(unique_districts),
        "unique_states": len(unique_states),
    }
    print(f"  Unique markets   : {len(unique_markets):,}")
    print(f"  Unique districts : {len(unique_districts):,}")
    print(f"  Unique states    : {len(unique_states):,}")

    # Per-commodity market counts
    print("\n  Per-commodity market counts:")
    pipeline_markets = [
        {"$group": {
            "_id": {"commodity": "$commodity", "market": "$market"},
        }},
        {"$group": {
            "_id": "$_id.commodity",
            "market_count": {"$sum": 1},
        }},
        {"$sort": {"market_count": -1}},
    ]
    per_commodity_markets = {}
    for r in collection.aggregate(pipeline_markets):
        per_commodity_markets[r["_id"]] = r["market_count"]
        print(f"    {r['_id']:20s}: {r['market_count']:>6,} markets")

    # Eligible series (>= 40 records)
    print("\n--- 4. Eligible training series (>= 40 records) ----------------")
    series_pipeline = [
        {"$group": {"_id": {"c": "$commodity", "m": "$market"}, "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 40}}},
        {"$group": {"_id": "$_id.c", "eligible": {"$sum": 1}}},
        {"$sort": {"eligible": -1}},
    ]
    total_eligible = 0
    eligible_per_commodity = {}
    for r in collection.aggregate(series_pipeline):
        eligible_per_commodity[r["_id"]] = r["eligible"]
        total_eligible += r["eligible"]
        print(f"  {r['_id']:20s}: {r['eligible']:>6,} eligible series")
    print(f"  {'TOTAL':20s}: {total_eligible:>6,}")

    # ------------------------------------------------------------------
    # 5. Sample records
    # ------------------------------------------------------------------
    print("\n--- 5. Sample records ------------------------------------------")
    samples = list(collection.find({}, {"_id": 0}).limit(3))
    for s in samples:
        print(f"  {s}")

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_documents": total_count,
        "per_commodity_counts": per_commodity,
        "date_ranges": date_ranges,
        "geography": {
            **geo_summary,
            "states_list": sorted(unique_states),
        },
        "per_commodity_markets": per_commodity_markets,
        "eligible_training_series": eligible_per_commodity,
        "total_eligible_series": total_eligible,
        "status": "PASS" if total_count > 0 and total_eligible > 0 else "FAIL",
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'=' * 65}")
    print(f"VALIDATION {'PASSED' if report['status'] == 'PASS' else 'FAILED'}")
    print(f"Report saved: {REPORT_PATH}")
    print(f"{'=' * 65}")

    return report


if __name__ == "__main__":
    run_verification()
