from datetime import datetime
import pandas as pd


def check_alerts(forecasts, historical_prices_30d):
    """
    forecasts: list of dicts [{"date": "...", "price": 1200}, ...]
    historical_prices_30d: list/array of the last 30 days prices
    Returns: alert_level, trigger_price, avg_price
    """
    if not historical_prices_30d:
        return "NORMAL", 0, 0

    avg_price = sum(historical_prices_30d) / len(historical_prices_30d)

    # Find the maximum predicted price in the horizon
    trigger_price = max(f["price"] for f in forecasts)

    if trigger_price > 2.0 * avg_price:
        return "CRITICAL", trigger_price, avg_price
    elif trigger_price > 1.5 * avg_price:
        return "HIGH", trigger_price, avg_price
    elif trigger_price > 1.2 * avg_price:
        return "MODERATE", trigger_price, avg_price
    else:
        return "NORMAL", trigger_price, avg_price
