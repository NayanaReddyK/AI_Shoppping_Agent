import os
import random
from google import genai

def get_gemini_client():
    """
    Returns a Gemini Client using a randomly selected API key from the .env file.
    """
    keys = []
    if os.environ.get("GEMINI_API_KEY"): keys.append(os.environ.get("GEMINI_API_KEY"))
    for i in range(1, 10):
        key = os.environ.get(f"GEMINI_API_KEY_{i}")
        if key: keys.append(key)
    if not keys: return None
    return genai.Client(api_key=random.choice(keys))

def get_groq_client():
    """
    Returns a Groq Client for blazing fast inference.
    """
    from groq import AsyncGroq
    from dotenv import load_dotenv
    import os
    load_dotenv(override=True)  # Force reload to pick up new keys without restarting server
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY not found in .env")
        return None
    return AsyncGroq(api_key=api_key)
