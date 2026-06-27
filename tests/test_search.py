import asyncio
from api_balancer import get_gemini_client
from google.genai import types
import json
from dotenv import load_dotenv
load_dotenv()

async def test_search():
    client = get_gemini_client()
    product_name = "Apple iPhone 12 Pro (Graphite, 128 GB)"
    
    prompt = f"""
    Find the current price of '{product_name}'.
    Use the Google Search tool to find the absolute best prices across ALL legitimate Indian websites.
    
    CRITICAL SEARCH INSTRUCTION: 
    The product name might be a very long Amazon title. If you search for the exact long title, Google will return ZERO results.
    You MUST extract just the core brand and model (e.g., "Apple iPhone 15 128GB" or "Tobo USB C Dual HDMI") and search for that instead.
    Search query recommendation: "[Core Brand and Model] price in India -cashify -refurbished -used"

    CRITICAL INSTRUCTIONS:
    1. If the product belongs to a specific brand (e.g., Apple, Sony, Samsung, Boat, Tobo), you MUST prioritize finding the price from the brand's OFFICIAL Indian website if it exists.
    2. After checking the official brand site, find 2 or 3 other legitimate Indian e-commerce competitors (like Amazon, Flipkart, Croma, Reliance, JioMart, etc.) that actually have the product.
    3. All prices MUST be in INR (₹). Do NOT return international sites or refurbished/used products.
    
    Return strictly JSON array: [{{"store": "Store/Brand Name", "title": "Exact Product Title on that site", "price": "Price in INR"}}]
    Do NOT use markdown code blocks like ```json. Return ONLY the raw JSON string.
    """
    
    print("Calling Gemini...")
    search_resp = await client.aio.models.generate_content(
        model='gemini-2.5-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
    )
    
    text = search_resp.text.strip()
    with open("search_debug.txt", "w", encoding="utf-8") as f:
        f.write("RAW TEXT:\n")
        f.write(text + "\n")
        f.write("---------\n")
    print("Wrote output to search_debug.txt")
    
    if text.startswith("```json"):
        text = text[7:-3].strip()
    elif text.startswith("```"):
        text = text[3:-3].strip()
        
    try:
        competitors = json.loads(text)
        print("Parsed JSON successfully!")
        print(competitors)
    except ValueError as e:
        print("JSON parse failed, running cleanup...")
        cleanup_resp = await client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=f"Extract competitor prices from this text into a JSON array of objects with keys 'store', 'title', 'price'. If no prices are found, return []. Text: {text}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        print("CLEANUP RAW:")
        print(cleanup_resp.text)
        competitors = json.loads(cleanup_resp.text)
        print("Cleaned JSON:")
        print(competitors)
        print("Is list?", isinstance(competitors, list))

if __name__ == "__main__":
    asyncio.run(test_search())
