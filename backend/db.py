import os
import pymongo
from datetime import datetime

def get_db_collection(collection_name="price_history"):
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        return None
        
    client = pymongo.MongoClient(mongo_uri)
    db = client["shopping_agent_db"]
    return db[collection_name]

def save_extracted_prices(product_name: str, stores_data: list):
    """
    Saves the extracted prices to MongoDB Cloud.
    """
    collection = get_db_collection()
    if collection is None:
        print("   [DB] MONGO_URI not set. Skipping database save.")
        return
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    records = []
    for data in stores_data:
        p_str = data.get("price", "")
        try:
            # Clean the string to get a raw float
            clean_price = "".join(c for c in p_str if c.isdigit() or c == '.')
            if clean_price:
                numeric_price = float(clean_price)
            else:
                continue # Skip if no valid number found
        except:
            continue
            
        record = {
            "product": product_name,
            "store": data.get("store"),
            "price_numeric": numeric_price,
            "price_string": p_str,
            "date": date_str,
            "timestamp": datetime.now()
        }
        records.append(record)
        
    if records:
        try:
            collection.insert_many(records)
            print(f"   [DB] Saved {len(records)} real-time prices to MongoDB Atlas!")
        except Exception as e:
            print(f"   [DB] Error saving to MongoDB: {e}")

def get_price_history(product_name: str, current_price_str: str) -> dict:
    """
    Queries MongoDB to build real historical data for Gemini.
    """
    print(f"\n[HISTORY PHASE] Querying MongoDB for '{product_name}' history...")
    
    collection = get_db_collection()
    if collection is None:
        print("   [DB] MONGO_URI not set. Returning empty history.")
        return {
            "status": "No historical data available (MONGO_URI not set)."
        }
        
    try:
        import re
        safe_product_name = re.escape(product_name)
        # Fetch all records for this product (case-insensitive)
        cursor = collection.find({"product": {"$regex": safe_product_name, "$options": "i"}})
        records = list(cursor)
        
        if not records:
            print("   [DB] No past records found for this product yet. Starting fresh!")
            return {
                "status": "New product. No past data available yet."
            }
            
        prices = [r["price_numeric"] for r in records if "price_numeric" in r]
        if not prices:
            return {"status": "No valid numeric prices found in history."}
            
        lowest = min(prices)
        highest = max(prices)
        average = sum(prices) / len(prices)
        
        history_data = {
            "all_time_lowest_price": round(lowest, 2),
            "all_time_highest_price": round(highest, 2),
            "average_price": round(average, 2),
            "total_historical_records_analyzed": len(records),
            "status": "Historical data retrieved from real MongoDB Cloud."
        }
        
        print("   Retrieved Real Historical Data from MongoDB:")
        for k, v in history_data.items():
            print(f"    - {k}: {v}")
            
        return history_data
        
    except Exception as e:
        print(f"   [DB] Error querying MongoDB: {e}")
        return {"error": str(e)}

def check_url_cache(url: str, ttl_hours: int = 1):
    """
    Checks if the exact URL was analyzed recently. Returns cached data if valid.
    """
    collection = get_db_collection("url_cache")
    if collection is None:
        return None
        
    try:
        from datetime import timedelta
        # Find the most recent cache for this URL
        cached = collection.find_one({"url": url}, sort=[("timestamp", pymongo.DESCENDING)])
        if cached:
            # Check if it's within the TTL (Time To Live)
            if datetime.now() - cached["timestamp"] < timedelta(hours=ttl_hours):
                print(f"   [CACHE HIT] Found fresh data for {url} (under {ttl_hours}h old)!")
                # Remove MongoDB's internal _id before returning to frontend
                del cached["_id"]
                return cached["data"]
            else:
                print(f"   [CACHE MISS] Data for {url} is expired (over {ttl_hours}h old). Fetching fresh prices.")
        return None
    except Exception as e:
        print(f"   [DB] Cache Error: {e}")
        return None

def save_to_url_cache(url: str, data: dict):
    """
    Saves the final AI analysis to the cache.
    """
    collection = get_db_collection("url_cache")
    if collection is None:
        return
        
    try:
        record = {
            "url": url,
            "data": data,
            "timestamp": datetime.now()
        }
        collection.insert_one(record)
        print(f"   [CACHE] Saved new analysis to MongoDB Cache for {url}")
    except Exception as e:
        print(f"   [DB] Cache Save Error: {e}")
