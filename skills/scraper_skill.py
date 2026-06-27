import asyncio
import sys
import os

# Dynamically resolve root path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import urllib.parse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SCRAPER_API_KEY = "your scraper api key"

async def fetch_html_via_mcp(session, target_url):
    print(f"   Fetching via ScraperAPI: {target_url}")
    print("   (This might take a few seconds as ScraperAPI bypasses CAPTCHAs...)")
    
    # URL encode the target URL so it can be passed as a query parameter
    encoded_url = urllib.parse.quote(target_url)
    
    # By using &render=false, ScraperAPI just fetches the raw HTML without executing JS.
    # This reduces the fetch time from ~15 seconds to ~3 seconds!
    scraper_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={encoded_url}&render=false"
    
    try:
        # The typescript MCP server exposes 'get_raw_text' to fetch URL contents
        result = await session.call_tool("get_raw_text", arguments={"url": scraper_url})
        raw_html = result.content[0].text if result.content else ""
        return raw_html
    except Exception as e:
        print(f"   Error fetching {target_url}: {e}")
        return ""

from bs4 import BeautifulSoup
import re
import json

async def extract_data_with_groq(raw_html, store_name, url):
    """
    Uses BeautifulSoup to extract JSON-LD schemas for 100% accurate price data.
    If no JSON-LD is found, falls back to cleaned HTML for Groq extraction.
    """
    import os
    from backend.api_balancer import get_groq_client
    
    client = get_groq_client()
    if not client:
        print("   No GROQ_API_KEY found in .env. Returning dummy data.")
        return {"store": store_name, "title": "Error: No Groq Key", "price": "Error"}
    
    # 1. DETERMINISTIC PARSING (The Flipshope Approach)
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Pre-extract Title for deterministic parsers
    # Try to find clean product names first before falling back to the messy SEO <title> tag
    clean_title = soup.find('span', {'id': 'productTitle'}) or soup.find('span', {'class': 'B_NuCI'}) or soup.find('span', {'class': 'VU-Tz5'})
    if clean_title:
        page_title = clean_title.text.strip()
    else:
        title_tag = soup.find('title')
        page_title = title_tag.text.strip() if title_tag else "Unknown Product"
    
    # Native Amazon Parser
    if "Amazon" in store_name:
        price_tag = soup.find('span', {'class': 'a-price-whole'}) or soup.find('span', {'id': 'priceblock_ourprice'})
        if price_tag:
            price_text = price_tag.text.strip().replace(',', '')
            return {"store": store_name, "title": page_title, "price": f"₹{price_text}"}
            
    # Native Flipkart Parser
    elif "Flipkart" in store_name:
        price_tag = soup.find('div', {'class': 'Nx9bqj CxhGGd'}) or soup.find('div', {'class': '_30jeq3 _16Jk6d'})
        if price_tag:
            price_text = price_tag.text.strip()
            return {"store": store_name, "title": page_title, "price": price_text}

    # 2. JSON-LD EXTRACTOR (Fast AI Fallback)
    json_ld_data = []
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string:
            try:
                data = json.loads(script.string.strip())
                json_ld_data.append(data)
            except:
                pass
                
    if json_ld_data:
        # If we found JSON-LD, we send only the JSON to Groq! Lightning fast and 100% accurate.
        data_to_analyze = json.dumps(json_ld_data)[:100000]
        prompt = f"""
        You are an expert Data Extractor for an AI Shopping Agent.
        I am providing you with the exact JSON-LD SEO schema from {store_name}.
        URL: {url}
        
        CRITICAL INSTRUCTIONS:
        1. Extract the CLEANED name of the main product (Brand + Model + Key Specifications). REMOVE all promotional words, store names, and SEO spam. Make it a universal search term.
        2. Extract the CURRENT LIVE PRICE of this exact product (look for 'offers', 'price', 'priceCurrency'). 
        3. Do NOT extract the original MSRP. Only the final discounted price.
        4. If it's a Search Results page JSON, find the FIRST non-sponsored exact match product.
        
        Return JSON object exactly with keys: 'store', 'title', 'price'.
        JSON Data:
        {data_to_analyze}
        """
    else:
        # FALLBACK: If no JSON-LD, clean the HTML and send it.
        clean_html = re.sub(r'<script.*?</script>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<style.*?</style>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        truncated_html = clean_html[:100000] # Groq LLaMA3 has 8k or 128k context depending on model. We use 100k for versatile.
        
        prompt = f"""
        You are an expert Data Extractor for an AI Shopping Agent.
        I am providing you with the HTML of a product page or search results page from {store_name}.
        URL: {url}
        
        CRITICAL INSTRUCTIONS:
        1. Extract the CLEANED name of the main product (Brand + Model + Key Specifications). REMOVE all promotional words, store names, and SEO spam. Make it a universal search term.
        2. Extract the CURRENT LIVE PRICE of this exact product. 
        3. Do NOT extract the original MSRP (strikethrough price). Only the final discounted price.
        4. If this is a Search Results page, find the FIRST non-sponsored exact match for the product and extract its price. Do NOT extract the price for accessories like cases or cables.
        
        Return JSON object exactly with keys: 'store', 'title', 'price'.
        HTML Snippet:
        {truncated_html}
        """
        
    try:
        response = await client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        text = response.choices[0].message.content
        return json.loads(text)
    except Exception as e:
        print(f"   Groq Extraction Error: {e}")
        return {"store": store_name, "title": f"Groq API Error: {str(e)}", "price": "Error"}
