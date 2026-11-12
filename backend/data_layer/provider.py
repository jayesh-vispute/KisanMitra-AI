import os
import sys
from abc import ABC, abstractmethod
import pandas as pd
from typing import List

# Ensure we can import from backend root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from database import get_sync_collection

class DataProvider(ABC):
    @abstractmethod
    def get_historical_prices(self, commodity: str = None) -> pd.DataFrame:
        """Fetch historical prices as a Pandas DataFrame."""
        pass
    
    @abstractmethod
    def get_available_commodities(self) -> List[str]:
        """Discover unique available commodities."""
        pass

class MongoDataProvider(DataProvider):
    """Fetches real historical data from MongoDB (excludes synthetic kaggle data)."""
    
    def get_historical_prices(self, commodity: str = None) -> pd.DataFrame:
        db_market_prices = get_sync_collection("market_prices")
        # Filter out kaggle_generated to ensure synthetic data is isolated
        query = {"data_type": {"$ne": "kaggle_generated"}}
        if commodity:
            query["commodity"] = commodity
            
        cursor = db_market_prices.find(query, {"_id": 0})
        data_list = list(cursor)
        
        df = pd.DataFrame(data_list)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df["price"] = df["price"].astype(float)
        else:
            df = pd.DataFrame(columns=["commodity", "date", "price", "data_type"])
        return df
        
    def get_available_commodities(self) -> List[str]:
        db_market_prices = get_sync_collection("market_prices")
        query = {"data_type": {"$ne": "kaggle_generated"}}
        commodities = db_market_prices.distinct("commodity", query)
        return [c for c in commodities if c]

class SyntheticDataProvider(DataProvider):
    """Fetches synthetic development data from MongoDB."""
    
    def get_historical_prices(self, commodity: str = None) -> pd.DataFrame:
        db_market_prices = get_sync_collection("market_prices")
        query = {"data_type": "kaggle_generated"}
        if commodity:
            query["commodity"] = commodity
            
        cursor = db_market_prices.find(query, {"_id": 0})
        data_list = list(cursor)
        
        df = pd.DataFrame(data_list)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df["price"] = df["price"].astype(float)
        else:
            df = pd.DataFrame(columns=["commodity", "date", "price", "data_type"])
        return df

    def get_available_commodities(self) -> List[str]:
        db_market_prices = get_sync_collection("market_prices")
        query = {"data_type": "kaggle_generated"}
        commodities = db_market_prices.distinct("commodity", query)
        return [c for c in commodities if c]

def get_data_provider() -> DataProvider:
    """Factory to return the active DataProvider based on configuration."""
    data_source = os.getenv("DATA_SOURCE", "MONGODB").upper()
    
    if data_source == "SYNTHETIC":
        return SyntheticDataProvider()
    else:
        # Default to real historical data
        return MongoDataProvider()
