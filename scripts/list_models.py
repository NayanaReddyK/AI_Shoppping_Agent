import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)
data = response.json()

if 'models' in data:
    for m in data['models']:
        if 'generateContent' in m.get('supportedGenerationMethods', []):
            print(m['name'])
else:
    print(data)
