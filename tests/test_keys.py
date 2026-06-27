import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def test_keys():
    keys = []
    if os.environ.get("GEMINI_API_KEY"):
        keys.append(os.environ.get("GEMINI_API_KEY"))
    for i in range(1, 10):
        key = os.environ.get(f"GEMINI_API_KEY_{i}")
        if key:
            keys.append(key)
            
    if not keys:
        print("NO KEYS FOUND IN .ENV")
        return
        
    print(f"Found {len(keys)} keys to test.")
    
    for idx, key in enumerate(keys):
        print(f"\n--- Testing Key {idx} ---")
        client = genai.Client(api_key=key)
        try:
            resp = await client.aio.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents="Reply with the word 'HELLO'"
            )
            print(f"Key {idx} SUCCESS: {resp.text.strip()}")
        except Exception as e:
            print(f"Key {idx} FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_keys())
