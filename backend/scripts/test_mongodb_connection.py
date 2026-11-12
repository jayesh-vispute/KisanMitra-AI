import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import sync_client, sync_db


def test_mongodb_connection():
    try:
        # Check connection
        sync_client.admin.command("ping")
        print("MongoDB Atlas Connected successfully via TLS/certifi.")

        # List collections
        collections = sync_db.list_collection_names()
        print(f"Found {len(collections)} collections: {collections}")

        # Check documents in each collection
        for coll_name in collections:
            coll = sync_db[coll_name]
            count = coll.count_documents({})
            print(f"\nCollection: {coll_name} | Document Count: {count}")
            if count > 0:
                sample = coll.find_one({}, {"_id": 0})
                print(f"Sample Document: {sample}")

    except Exception as e:
        print(f"ERROR connecting to MongoDB: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_mongodb_connection()
