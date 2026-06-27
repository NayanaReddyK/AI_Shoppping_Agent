from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys
import os

# Dynamically resolve root path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from dotenv import load_dotenv

# Load variables from .env file into the environment instantly
load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from urllib.parse import urlparse

# Import our True Autonomous Agent
from skills.shopping_agent import run_agentic_loop

app = FastAPI()

class SearchQuery(BaseModel):
    url: str

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

def get_store_name(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "amazon" in domain: return "Amazon"
    if "flipkart" in domain: return "Flipkart"
    if "croma" in domain: return "Croma"
    if "reliancedigital" in domain: return "Reliance Digital"
    if "myntra" in domain: return "Myntra"
    if "nykaa" in domain: return "Nykaa"
    if "vijaysales" in domain: return "Vijay Sales"
    parts = domain.replace("www.", "").split(".")
    if len(parts) > 2 and parts[0] in ["in", "store", "shop"]:
        return parts[1].capitalize()
    return parts[0].capitalize()

def normalize_url_for_cache(url: str) -> str:
    """
    Cleans up URLs to be used as identical Cache Keys.
    Strips out tracking tokens, ref tags, and unnecessary query parameters.
    """
    from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
    import re
    
    parsed = urlparse(url)
    
    # Clean the path (specifically for Amazon tracking like /ref=sr_1_1)
    path = parsed.path
    if "amazon" in parsed.netloc.lower():
        path = re.sub(r'/ref=.*', '', path)
        
    # Clean query parameters (keep important ones like 'pid' for Flipkart, discard 'utm', 'tag')
    query_params = parse_qsl(parsed.query)
    clean_params = []
    for k, v in query_params:
        k_lower = k.lower()
        if k_lower in ['pid', 'id', 'sku', 'item_id', 'product_id']:
            clean_params.append((k, v))
            
    clean_query = urlencode(clean_params)
    
    # Rebuild the URL without fragments or tracking junk
    normalized = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, clean_query, ''))
    
    # Strip trailing slashes to ensure exact matches
    return normalized.rstrip('/')

from backend.db import check_url_cache, save_to_url_cache

@app.post("/api/analyze")
async def analyze_product(query: SearchQuery):
    provided_url = query.url
    if not provided_url.startswith("http"):
        provided_url = "https://" + provided_url
        
    base_store = get_store_name(provided_url)
    
    # Generate a clean, universal cache key for this product
    cache_key = normalize_url_for_cache(provided_url)
    
    # [NEW] Caching Layer Intercept! 
    # TTL is set to 1 hour. If we have fresh data, we skip the AI completely.
    cached_result = check_url_cache(cache_key, ttl_hours=1)
    if cached_result:
        print(f"[CACHE HIT] Found active cache for: {cache_key}")
        return cached_result

    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-server-fetch-typescript"],
    )

    # Initialize the secure MCP connection, but do NOT execute tasks directly.
    # We hand over complete control of the session to the LLM Brain!
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # The True Agent takes over here
            try:
                result = await run_agentic_loop(session, provided_url, base_store)
                
                if "error" not in result:
                    save_to_url_cache(cache_key, result)
                    
                return result
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                return {"error": f"Backend Crash: {str(e)}"}
