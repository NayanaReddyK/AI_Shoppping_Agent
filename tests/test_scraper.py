import time
import requests
import urllib.parse

SCRAPER_API_KEY = "e560f5e5311f2a7650cd461385039ac0"
url = "https://www.amazon.in/dp/B0CHX1W1XY"
encoded_url = urllib.parse.quote(url)

scraper_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={encoded_url}&render=false"

start_time = time.time()
print("Fetching from ScraperAPI...")
res = requests.get(scraper_url)
print(f"Status: {res.status_code}")
print(f"Time taken: {time.time() - start_time:.2f} seconds")
print(f"HTML length: {len(res.text)}")
