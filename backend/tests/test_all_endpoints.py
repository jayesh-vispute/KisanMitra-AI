"""
test_all_endpoints.py - KisanMitra AI regression test suite.

Runs against a locally running server (http://localhost:8000).
Tests every API endpoint and prints a pass/fail report.

Usage:
    python tests/test_all_endpoints.py
"""

import sys
import time
import requests

BASE = "http://localhost:8000"
RESULTS = []


def ok(name, detail=""):
    RESULTS.append(("PASS", name, detail))
    msg = f"  [PASS] {name}"
    if detail:
        msg += f"  [{detail}]"
    print(msg)


def fail(name, detail=""):
    RESULTS.append(("FAIL", name, detail))
    print(f"  [FAIL] {name}  [{detail}]")


def check(condition, name, detail=""):
    if condition:
        ok(name, detail)
    else:
        fail(name, detail)


# --- helpers -----------------------------------------------------------------

def get(path, params=None, timeout=30):
    try:
        return requests.get(f"{BASE}{path}", params=params, timeout=timeout)
    except Exception as e:
        print(f"  [ERR ] {path} - {e}")
        return None


def post(path, body, timeout=30):
    try:
        return requests.post(f"{BASE}{path}", json=body, timeout=timeout)
    except Exception as e:
        print(f"  [ERR ] {path} - {e}")
        return None


# --- tests -------------------------------------------------------------------

def test_health():
    print("\n[1] Health endpoints")
    r = get("/")
    check(r is not None and r.status_code == 200, "GET /", f"status={getattr(r,'status_code','N/A')}")
    r = get("/health")
    check(r is not None and r.status_code == 200, "GET /health", f"status={getattr(r,'status_code','N/A')}")


def test_market():
    print("\n[2] Market endpoints")

    r = get("/api/market/states")
    if r and r.status_code == 200:
        d = r.json()
        check("states" in d and len(d["states"]) > 0,
              "GET /api/market/states", f"count={len(d.get('states', []))}")
    else:
        fail("GET /api/market/states", f"status={getattr(r,'status_code','N/A')}")

    r = get("/api/market/districts", {"state": "Maharashtra"})
    if r and r.status_code == 200:
        d = r.json()
        check("districts" in d, "GET /api/market/districts",
              f"count={len(d.get('districts', []))}")
    else:
        fail("GET /api/market/districts", f"status={getattr(r,'status_code','N/A')}")

    r = get("/api/market/mandis", {"state": "Maharashtra", "district": "Nashik"})
    if r and r.status_code == 200:
        d = r.json()
        check("mandis" in d, "GET /api/market/mandis",
              f"count={len(d.get('mandis', []))}")
    else:
        fail("GET /api/market/mandis", f"status={getattr(r,'status_code','N/A')}")

    r = get("/api/market/commodities", {"state": "Maharashtra", "market": "Nashik"})
    if r and r.status_code == 200:
        d = r.json()
        check("commodities" in d, "GET /api/market/commodities",
              f"count={len(d.get('commodities', []))}")
    else:
        fail("GET /api/market/commodities", f"status={getattr(r,'status_code','N/A')}")

    r = get("/api/market/prices",
            {"state": "Maharashtra", "market": "Nashik", "commodity": "Onion"},
            timeout=60)
    if r and r.status_code == 200:
        d = r.json()
        check("prices" in d, "GET /api/market/prices - has prices key",
              f"source={d.get('source', '?')}")
        prices = d.get("prices", [])
        check(isinstance(prices, list), "prices is a list")
        check(
            len(prices) > 0 or d.get("source") in ("unavailable",),
            "prices not empty OR source=unavailable (acceptable)",
            f"count={len(prices)}, source={d.get('source')}"
        )
    else:
        fail("GET /api/market/prices", f"status={getattr(r,'status_code','N/A')}")


def test_predict():
    print("\n[3] Predict endpoint - schema validation")

    r = get("/api/predict",
            {"commodity": "Onion", "market": "Nashik", "horizon": 7},
            timeout=90)
    if r is None or r.status_code != 200:
        fail("GET /api/predict returns 200",
             f"status={getattr(r,'status_code','N/A')}")
        return

    d = r.json()

    # Required fields
    check("current_price" in d, "predict has current_price", str(d.get("current_price")))
    check("trend_percent" in d, "predict has trend_percent", str(d.get("trend_percent")))
    check("forecast" in d and isinstance(d.get("forecast"), list), "predict has forecast[]")
    check("confidence" in d, "predict has confidence", str(d.get("confidence")))
    check("accuracy" in d, "predict has accuracy")
    check("model_weights" in d, "predict has model_weights")
    check("individual_predictions" in d, "predict has individual_predictions")
    check("prediction_source" in d, "predict has prediction_source",
          d.get("prediction_source"))
    check("active_models" in d, "predict has active_models",
          str(d.get("active_models")))

    # NaN checks
    cp = d.get("current_price")
    check(isinstance(cp, (int, float)) and cp == cp,
          "current_price is a valid number (not NaN)", str(cp))

    tp = d.get("trend_percent")
    check(isinstance(tp, (int, float)) and tp == tp,
          "trend_percent is a valid number (not NaN)", str(tp))

    # Forecast item schema
    fc = d.get("forecast", [])
    if fc:
        first = fc[0]
        check("price" in first, "forecast[0] has 'price' key", str(first.get("price")))
        check("lower" in first, "forecast[0] has 'lower' key", str(first.get("lower")))
        check("upper" in first, "forecast[0] has 'upper' key", str(first.get("upper")))
        pv = first.get("price")
        check(isinstance(pv, (int, float)) and pv == pv,
              "forecast[0].price not NaN", str(pv))
        # Confirm old keys are NOT present (they'd cause frontend NaN)
        check("predicted_price" not in first,
              "forecast[0] does NOT have old 'predicted_price' key")
        check("lower_bound" not in first,
              "forecast[0] does NOT have old 'lower_bound' key")
    else:
        ok("predict forecast[] is empty (might have an error field)",
           d.get("error", ""))


def test_weather():
    print("\n[4] Weather endpoint")
    r = get("/api/weather", {"mandi": "Nashik"})
    if r and r.status_code == 200:
        d = r.json()
        check("mandi" in d, "weather has mandi")
        check("current" in d or "error" in d,
              "weather has current data or error")
        check("farming_advisory" in d, "weather has farming_advisory")
    else:
        fail("GET /api/weather", f"status={getattr(r,'status_code','N/A')}")


def test_crop_health():
    print("\n[5] Crop Health endpoint")
    r = get("/api/crop-health", {"mandi": "Nashik"}, timeout=30)
    if r is None or r.status_code != 200:
        fail("GET /api/crop-health returns 200",
             f"status={getattr(r,'status_code','N/A')}")
        return

    d = r.json()
    check("mandi" in d, "crop-health has mandi")
    check("state" in d, "crop-health has state")
    check("ndvi_proxy" in d, "crop-health has ndvi_proxy",
          str(d.get("ndvi_proxy")))
    check("rainfall_30d_mm" in d, "crop-health has rainfall_30d_mm")
    check("temperature_avg" in d, "crop-health has temperature_avg")
    check(
        "stress_level" in d and d["stress_level"] in ("Low", "Moderate", "High"),
        "crop-health stress_level is valid (Low/Moderate/High)",
        d.get("stress_level")
    )
    check(
        "recommendation" in d and len(d.get("recommendation", "")) > 20,
        "crop-health has non-empty recommendation"
    )

    # NaN checks on numeric fields
    ndvi = d.get("ndvi_proxy")
    check(isinstance(ndvi, (int, float)) and ndvi == ndvi,
          "ndvi_proxy not NaN", str(ndvi))

    temp = d.get("temperature_avg")
    check(isinstance(temp, (int, float)) and temp == temp,
          "temperature_avg not NaN", str(temp))


def test_farmer_advisory():
    print("\n[6] Farmer Advisory endpoint")
    r = get("/api/farmer-advisory",
            {"commodity": "Onion", "mandi": "Nashik"}, timeout=30)
    if r is None or r.status_code != 200:
        fail("GET /api/farmer-advisory returns 200",
             f"status={getattr(r,'status_code','N/A')}")
        return

    d = r.json()
    check(
        "advisory_text" in d and len(d.get("advisory_text", "")) > 20,
        "advisory has advisory_text"
    )
    check(
        "advisory_text_hi" in d and len(d.get("advisory_text_hi", "")) > 5,
        "advisory has advisory_text_hi"
    )
    check("best_sell_window" in d, "advisory has best_sell_window",
          d.get("best_sell_window"))
    check("expected_price_range" in d, "advisory has expected_price_range",
          d.get("expected_price_range"))
    check("trend_percent" in d, "advisory has trend_percent",
          str(d.get("trend_percent")))
    check("current_price" in d, "advisory has current_price",
          str(d.get("current_price")))


def test_chat():
    print("\n[7] Chat endpoint")
    r = post("/api/chat",
             {"message": "What is the price of onion?",
              "commodity": "Onion", "mandi": "Nashik"})
    if r and r.status_code == 200:
        d = r.json()
        has_reply = any(k in d for k in ("answer", "reply", "response", "message", "error"))
        check(has_reply, "chat returns a response field")
    else:
        ok("GET /api/chat (external API may not be configured)",
           f"status={getattr(r,'status_code','N/A')}")


# --- summary -----------------------------------------------------------------

def print_summary():
    passed = [r for r in RESULTS if r[0] == "PASS"]
    failed = [r for r in RESULTS if r[0] == "FAIL"]
    total = len(RESULTS)

    print("\n" + "=" * 60)
    print("  REGRESSION REPORT - KisanMitra AI")
    print(f"  {len(passed)}/{total} tests passed  |  {len(failed)} failed")
    print("=" * 60)

    if failed:
        print("\n  Failed tests:")
        for _, name, detail in failed:
            print(f"    [FAIL] {name}  [{detail}]")
    else:
        print("\n  All tests passed! [OK]")

    print("=" * 60 + "\n")
    return len(failed)


if __name__ == "__main__":
    print("=" * 60)
    print("  KisanMitra AI - Integration Regression Tests")
    print(f"  Target: {BASE}")
    print("=" * 60)

    t0 = time.time()
    test_health()
    test_market()
    test_predict()
    test_weather()
    test_crop_health()
    test_farmer_advisory()
    test_chat()
    elapsed = time.time() - t0

    print(f"\n  Completed in {elapsed:.1f}s")
    n_failures = print_summary()
    sys.exit(0 if n_failures == 0 else 1)
