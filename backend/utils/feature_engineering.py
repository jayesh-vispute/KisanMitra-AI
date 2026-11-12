import pandas as pd

def create_features(group):
    # Ensure modal_price is numeric
    group["modal_price"] = pd.to_numeric(group["modal_price"], errors="coerce")
    
    group["price_lag_7"] = group["modal_price"].shift(7)
    group["price_lag_14"] = group["modal_price"].shift(14)
    group["price_lag_30"] = group["modal_price"].shift(30)
    group["rolling_mean_7"] = group["modal_price"].rolling(window=7).mean()
    group["rolling_mean_30"] = group["modal_price"].rolling(window=30).mean()
    group["rolling_std_7"] = group["modal_price"].rolling(window=7).std().fillna(0)

    exp1 = group["modal_price"].ewm(span=12, adjust=False).mean()
    exp2 = group["modal_price"].ewm(span=26, adjust=False).mean()
    group["macd"] = exp1 - exp2

    group["day_of_week"] = group["date"].dt.dayofweek
    group["month"] = group["date"].dt.month
    return group.dropna()
