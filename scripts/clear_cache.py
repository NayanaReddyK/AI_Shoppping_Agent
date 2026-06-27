import sys
import os

# Dynamically resolve root path for imports and .env loading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymongo
from dotenv import load_dotenv

load_dotenv()

def clear_cache():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("No MONGO_URI")
        return
        
    client = pymongo.MongoClient(mongo_uri)
    db = client["shopping_agent_db"]
    collection = db["url_cache"]
    
    deleted = collection.delete_many({})
    print(f"Deleted {deleted.deleted_count} cached URLs.")

if __name__ == "__main__":
    clear_cache()
