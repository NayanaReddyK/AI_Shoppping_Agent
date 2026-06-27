import os
from google import genai
from google.genai import types
import time

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No API key")
else:
    client = genai.Client(api_key=api_key)

    print("Testing Gemini Search Grounding...")
    start = time.time()
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Search the web and find the current exact live price of "Moondrop Chu II IEM" on Amazon India and HeadphoneZone. Return the exact prices.',
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
    )
    print(response.text)
    print(f"Time taken: {time.time() - start:.2f} seconds")
