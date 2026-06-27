import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def test_search():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = f"""
    Find the current price of 'Tobo USB C To 7.4Mm Laptop Charging Adapter'.
    You MUST use the exact following Google Search query to bypass Amazon/Flipkart SEO dominance:
    "Tobo USB C To 7.4Mm Laptop Charging Adapter" site:croma.com OR site:reliancedigital.in OR site:vijaysales.com

    Find 1 or 2 competitors from those exact sites.
    Return strictly JSON array: [{{"store": "Name", "title": "Product Title", "price": "Price"}}]
    Do NOT use markdown code blocks like ```json. Return ONLY the raw JSON string.
    """
    
    print("Sending request...")
    try:
        search_resp = await client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        with open("search_out.txt", "w", encoding="utf-8") as f:
            f.write(search_resp.text)
        print("Success! Output saved to search_out.txt")
    except Exception as e:
        print("Exception:", str(e))

asyncio.run(test_search())
