import os
import certifi
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
db = client["kisanmitra_ai"]
collection = db["market_cache"]

now = datetime.now(timezone.utc)

docs = [
    {"cache_key": "states", "data": ["Maharashtra", "Gujarat", "Karnataka"], "cached_at": now},
    {"cache_key": "districts_Maharashtra", "data": ["Pune", "Nashik", "Mumbai"], "cached_at": now},
    {"cache_key": "mandis_Maharashtra_Pune", "data": ["Pune", "Khed", "Junnar"], "cached_at": now},
    {"cache_key": "commodities_Maharashtra_Pune_Pune", "data": ["Onion", "Tomato", "Potato"], "cached_at": now},
]

for doc in docs:
    collection.update_one({"cache_key": doc["cache_key"]}, {"$set": doc}, upsert=True)

print("Mock data seeded successfully!")
