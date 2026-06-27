import requests
import time
from bs4 import BeautifulSoup
import urllib.parse

SCRAPER_API_KEY = "e560f5e5311f2a7650cd461385039ac0"
url = "https://www.amazon.in/dp/B0CHX1W1XY"
encoded_url = urllib.parse.quote(url)

print("Testing ScraperAPI without render=true...")
start = time.time()
scraper_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={encoded_url}&render=false"
response = requests.get(scraper_url)
duration = time.time() - start

print(f"Time taken: {duration:.2f} seconds")
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')
json_ld_data = []
for script in soup.find_all('script', type='application/ld+json'):
    json_ld_data.append(script.string)
    
print(f"Found {len(json_ld_data)} JSON-LD blocks!")
if json_ld_data:
    print("Preview of JSON-LD:")
    print(json_ld_data[0][:200])
