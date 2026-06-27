import os
import pymongo
import sys
from dotenv import load_dotenv

# Dynamically resolve root path for imports and .env loading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def print_database_report():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("[ERROR] MONGO_URI not found in environment!")
        return
        
    client = pymongo.MongoClient(mongo_uri)
    db = client["shopping_agent_db"]
    history_col = db["price_history"]
    cache_col = db["url_cache"]
    
    # 1. Generate Markdown Report file
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug", "price_history_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# MongoDB Atlas Database Contents Report\n\n")
        f.write(f"Generated on: {pymongo.__version__} client connection\n\n")
        
        # Summary counts
        h_count = history_col.count_documents({})
        c_count = cache_col.count_documents({})
        f.write("## Database Collection Summary\n")
        f.write(f"* **Price History Logs (`price_history` collection)**: {h_count} records\n")
        f.write(f"* **URL Analysis Caches (`url_cache` collection)**: {c_count} records\n\n")
        
        # Unique products list
        unique_products = history_col.distinct("product")
        f.write("## Seeded Products in Database\n")
        for prod in unique_products:
            f.write(f"### 📦 {prod}\n")
            
            # Get stats for this product
            records = list(history_col.find({"product": prod}))
            prices = [r["price_numeric"] for r in records if "price_numeric" in r]
            
            if prices:
                low = min(prices)
                high = max(prices)
                avg = sum(prices) / len(prices)
                f.write(f"* **Records Count**: {len(records)} pricing points\n")
                f.write(f"* **All-Time Lowest**: ₹{low:,.2f}\n")
                f.write(f"* **All-Time Highest**: ₹{high:,.2f}\n")
                f.write(f"* **6-Month Average**: ₹{avg:,.2f}\n\n")
                
                # Render a brief table of recent 5 entries
                f.write("| Date | Store | Price |\n")
                f.write("| --- | --- | --- |\n")
                for r in records[:5]:
                    f.write(f"| {r.get('date')} | {r.get('store')} | {r.get('price_string')} |\n")
                f.write("\n")
                
        # Cache list
        f.write("## Active Cached Search URLs\n")
        caches = list(cache_col.find({}))
        if caches:
            f.write("| Cached URL | Product Title | Timestamp |\n")
            f.write("| --- | --- | --- |\n")
            for c in caches:
                url = c.get("url", "")
                short_url = url[:60] + "..." if len(url) > 60 else url
                title = c.get("data", {}).get("product_name", "Unknown")
                ts = c.get("timestamp")
                f.write(f"| [{short_url}]({url}) | {title} | {ts} |\n")
        else:
            f.write("No URL searches currently cached.\n")
            
    print(f"Report successfully compiled and saved to: {report_path}")

if __name__ == "__main__":
    print_database_report()
