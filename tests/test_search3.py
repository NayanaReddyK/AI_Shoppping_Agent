import os
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)

async def main():
    api_key = os.environ.get("GEMINI_API_KEY_1") or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    product_name = "Apple iPhone 15 128GB"
    
    prompt = f"""
    Find the current price of '{product_name}'.
    Use the Google Search tool to find the absolute best prices across legitimate Indian websites.
    
    Search query recommendation: "{product_name} buy online India price"
    
    CRITICAL INSTRUCTIONS:
    1. EXCLUSIVE WHITELIST: You MUST ONLY extract prices for these top-tier stores: Amazon, Flipkart, Croma, Reliance Digital, Vijay Sales, Apple. 
    2. URL EXTRACTION: You MUST extract the exact direct link (URL) to the product page from the search result.
    
    Return strictly JSON array: [{{"store": "Store/Brand Name", "title": "Exact Product Title on that site", "price": "Price in INR", "url": "Exact URL of the product"}}]
    """

    print(f"Searching for {product_name}...")
    try:
        search_resp = await client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        print("--- RAW OUTPUT ---")
        print(search_resp.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
