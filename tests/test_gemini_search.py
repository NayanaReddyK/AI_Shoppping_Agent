import os
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)

async def test_gemini_search():
    api_key = os.environ.get("GEMINI_API_KEY_1") or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    product_name = "Noise Twist Go Round dial Smartwatch with BT Calling, 1.39\" Display, Metal Build, 100+ Watch Faces, IP68, Sleep Tracking, 100+ Sports Modes, 24/7 Heart Rate Monitoring (Silver Grey)"
    base_store = "Amazon"
    
    prompt = f"""
    You are a Perplexity-style smart shopping assistant. Your goal is to find the current price of this product on other major Indian e-commerce platforms.
    
    Raw Product Title from Source: "{product_name}"
    Original Store: {base_store}
    
    CRITICAL SEARCH INSTRUCTION:
    The Raw Product Title provided above is extremely messy, SEO-stuffed, and specific to the Original Store. If you search for it exactly, you will find 0 competitors!
    BEFORE using the Google Search tool, you MUST identify the clean Core Product Entity (Brand + Model + Key Spec). 
    For example, if the raw title is 'Noise Twist Go Round dial Smartwatch with BT Calling, 1.39 Display...', your clean search query must be 'Noise Twist Go Smartwatch buy online India'.
    Do NOT search the raw title. ALWAYS search for the clean Core Product Entity.
    
    Use the Google Search tool to find the absolute best prices across legitimate Indian websites.
    You MUST find prices from at least 3-4 DIFFERENT stores. Do not stop after finding just one.

    CRITICAL INSTRUCTIONS:
    1. LEGITIMATE RETAILERS ONLY: Extract prices from ALL legitimate e-commerce retailers (e.g., Amazon, Flipkart, Croma, Reliance Digital, Vijay Sales, Tata CLiQ, Myntra, Nykaa, JioMart, Headphone Zone, and official brand stores like Apple, Samsung, Sony, JBL, {base_store}).
    2. STRICT BLACKLIST: You MUST IGNORE ALL price aggregators, review sites, and sketchy importers. Completely IGNORE: Smartprix, Buyhatke, 91mobiles, Gadgets360, Cashify, MySmartPrice, FoneZone, Ubuy, Mahavir Mobile, India Today, NDTV.
    3. BANNED PRICES: If the search result says "EMI", "Wholesale", "null", or doesn't show a clear number, DO NOT include that store in your array! Skip it entirely.
    4. ACCESSORY FILTER: Ensure the price matches the actual requested product. Do NOT include cheap accessories (like silicone cases, ear tips, or chargers). If a price is suspiciously low (e.g., ₹13 for a ₹700 item), it is an accessory. IGNORE IT.
    
    Return strictly JSON array: [{{"store": "Store/Brand Name", "title": "Exact Product Title on that site", "price": "Price in INR"}}]
    Do NOT use markdown code blocks like ```json. Return ONLY the raw JSON string.
    """

    print("Executing Gemini Search...")
    try:
        search_resp = await client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.0
            )
        )
        with open("gemini_search_test.txt", "w", encoding="utf-8") as f:
            f.write(str(search_resp))
        print("Raw output saved to gemini_search_test.txt")
        
        # Let's inspect the grounding metadata to see the search query!
        if getattr(search_resp, 'candidates', None) and len(search_resp.candidates) > 0:
            candidate = search_resp.candidates[0]
            if getattr(candidate, 'grounding_metadata', None):
                print("\n--- GROUNDING METADATA ---")
                gm = candidate.grounding_metadata
                if hasattr(gm, 'web_search_queries'):
                    print("Web Search Queries:", gm.web_search_queries)
                else:
                    print("No web_search_queries in grounding metadata")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_search())
