import os
import pymongo

mongo_uri = os.environ.get("MONGO_URI")
print(f"Connecting to MongoDB Atlas...")
try:
    client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client["shopping_agent_db"]
    collection = db["price_history"]
    
    # Insert a test record
    result = collection.insert_one({"product": "Test Connection", "price_numeric": 999})
    print(f"   Successfully inserted test record with ID: {result.inserted_id}")
    
    # Read it back
    doc = collection.find_one({"_id": result.inserted_id})
    print(f"   Successfully read test record: {doc['product']} - {doc['price_numeric']}")
    
    # Clean up
    collection.delete_one({"_id": result.inserted_id})
    print("   Successfully cleaned up test record.")
    print("\nDATABASE CONNECTION IS FLAWLESS! ")
except Exception as e:
    print(f"Connection Failed: {e}")
