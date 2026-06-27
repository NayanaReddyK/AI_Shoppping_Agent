import sys
import os

# Dynamically resolve root path for imports and .env loading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymongo
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

load_dotenv()

def seed_historical_data():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("[ERROR] MONGO_URI not found in environment!")
        return
        
    client = pymongo.MongoClient(mongo_uri)
    db = client["shopping_agent_db"]
    collection = db["price_history"]
    
    # Define baseline structures for popular items to seed
    seed_products = [
        {
            "name": "Noise Twist Go Round dial Smartwatch with BT Calling",
            "stores": ["Amazon", "Flipkart", "Croma"],
            "base_price": 1499.0,
            "variation_range": 0.15 # Up to 15% fluctuation
        },
        {
            "name": "Apple AirPods Pro (2nd Generation) with MagSafe Case",
            "stores": ["Amazon", "Flipkart", "Reliance Digital", "Apple Store"],
            "base_price": 24900.0,
            "variation_range": 0.12
        },
        {
            "name": "Samsung Galaxy S25 5G",
            "stores": ["Amazon", "Flipkart", "Reliance Digital", "Samsung India"],
            "base_price": 62999.0,
            "variation_range": 0.10
        },
        {
            "name": "Apple iPhone 16 Pro 128 GB",
            "stores": ["Amazon", "Flipkart", "Croma", "Apple Store"],
            "base_price": 119900.0,
            "variation_range": 0.08
        }
    ]
    
    print("Seeding price history database...")
    total_records = 0
    
    # Create history spanning the last 90 days with random periodic intervals
    for product in seed_products:
        print(f" -> Generating records for: {product['name']}")
        
        # Check if records already exist for this product to prevent duplicate seeding
        existing = collection.count_documents({"product": {"$regex": product["name"][:15], "$options": "i"}})
        if existing > 10:
            print(f"    Product already has {existing} historical records. Skipping.")
            continue
            
        records = []
        for days_ago in range(90, 0, -3): # Every 3 days
            date = datetime.now() - timedelta(days=days_ago)
            date_str = date.strftime("%Y-%m-%d")
            
            # Simulate discount fluctuations (sales events, minor variations)
            discount_factor = 1.0 - (random.uniform(-0.05, product["variation_range"]))
            
            for store in product["stores"]:
                # Introduce slight price variations between stores
                store_price = round(product["base_price"] * discount_factor * random.uniform(0.97, 1.03), 2)
                
                record = {
                    "product": product["name"],
                    "store": store,
                    "price_numeric": store_price,
                    "price_string": f"₹{int(store_price):,}",
                    "date": date_str,
                    "timestamp": date
                }
                records.append(record)
                
        if records:
            collection.insert_many(records)
            total_records += len(records)
            print(f"    Seeded {len(records)} pricing intervals.")
            
    print(f"\nSuccessfully populated {total_records} historical price points to MongoDB Atlas!")

if __name__ == "__main__":
    seed_historical_data()
