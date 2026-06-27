from duckduckgo_search import DDGS
import urllib.parse

def get_product_urls(product_name: str) -> list:
    """
    Dynamically searches DuckDuckGo for the exact product URLs.
    If DuckDuckGo fails or returns empty, falls back to direct search URLs.
    """
    print(f"\n[SEARCH PHASE] Dynamically searching the web for: {product_name}")
    
    stores = [
        ("Amazon", "site:amazon.in"),
        ("Flipkart", "site:flipkart.com")
    ]
    
    urls = []
    
    try:
        with DDGS() as ddgs:
            for store_name, site_operator in stores:
                query = f"{product_name} {site_operator}"
                try:
                    search_results = list(ddgs.text(query, max_results=1))
                    
                    if search_results and "href" in search_results[0]:
                        url = search_results[0]["href"]
                        print(f"   [{store_name}] Found exact URL: {url}")
                        urls.append((store_name, url))
                    else:
                        print(f"   [{store_name}] DuckDuckGo returned no exact URLs.")
                except Exception as e:
                    print(f"   [{store_name}] Search error: {e}")
    except Exception as e:
        print(f"   [!] DuckDuckGo initialization error: {e}")
        
    # FALLBACK MECHANISM: If DuckDuckGo fails (returns empty list), construct direct search URLs!
    if not urls:
        print("\n   [!] DuckDuckGo search failed or rate-limited. Activating Fallback Mechanism...")
        encoded_query = urllib.parse.quote_plus(product_name)
        
        amazon_url = f"https://www.amazon.in/s?k={encoded_query}"
        print(f"   [Amazon Fallback] Using direct search: {amazon_url}")
        urls.append(("Amazon", amazon_url))
        
        flipkart_url = f"https://www.flipkart.com/search?q={encoded_query}"
        print(f"   [Flipkart Fallback] Using direct search: {flipkart_url}")
        urls.append(("Flipkart", flipkart_url))

    return urls
