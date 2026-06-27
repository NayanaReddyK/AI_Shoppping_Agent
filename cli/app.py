import asyncio
import sys
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import our custom modules
from searcher import get_product_urls
from db import save_extracted_prices, get_price_history
from shopping_agent import get_shopping_recommendation
# Reusing extraction functions from main.py
from main import fetch_html_via_mcp, extract_data_with_gemini

async def main():
    print("="*60)
    print("   AI SHOPPING AGENT - DYNAMIC PRICE PREDICTOR")
    print("="*60)
    
    product_query = input("\nEnter the product you want to buy (e.g. 'Samsung Galaxy S25'): ").strip()
    if not product_query:
        print("Product query cannot be empty.")
        return
        
    # Phase 1: Dynamic Search
    dynamic_urls = get_product_urls(product_query)
    
    if not dynamic_urls:
        print("\nNo URLs found for this product. Exiting.")
        return

    # Initialize MCP Fetch Server
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-server-fetch-typescript"],
    )

    print("\n[EXTRACTION PHASE] Starting Fetch MCP Server...")
    
    results = []
    product_name_extracted = product_query
    
    # Phase 2: Extraction via ScraperAPI
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            for store_name, url in dynamic_urls:
                html = await fetch_html_via_mcp(session, url)
                if html:
                    print(f"   Successfully bypassed bot detection! Downloaded {len(html)} bytes of HTML.")
                    print("   Asking Gemini to parse the HTML for price and title...")
                    data = extract_data_with_gemini(html, store_name, url)
                    
                    if data:
                        if data.get("title") not in ["Not found", "Error", "Error: No Gemini Key"]:
                            product_name_extracted = data.get("title")
                        
                        results.append(data)
                        print(f"   Extracted: {data.get('title')} - {data.get('price')}\n")
    
    extracted_data = {
        "product": product_name_extracted,
        "stores": results
    }
    
    # Phase 3: Cloud Database & Historical Tracking
    print("\n[DATABASE PHASE] Interacting with MongoDB Atlas...")
    save_extracted_prices(product_name_extracted, results)
    
    # We no longer need the dummy baseline price because we pull real history!
    history_data = get_price_history(product_name_extracted, "")
    
    print("\n" + "-"*50)
    print("[REASONING PHASE] Calling Gemini API to predict future price...")
    
    # Phase 4: Gemini Prediction & Recommendation
    recommendation = get_shopping_recommendation(extracted_data, history_data)
    
    print("\n" + "="*50)
    print("FINAL AGENT PREDICTION & RECOMMENDATION:")
    print("="*50)
    print(json.dumps(recommendation, indent=4))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
