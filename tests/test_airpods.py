import asyncio
import os
import httpx

async def main():
    url = "http://localhost:8000/api/analyze"
    payload = {"url": "https://www.sangeethamobiles.com/product/apple-airpods-4"}
    
    # We will simulate the same request the user made
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=60.0)
            print(resp.json())
        except Exception as e:
            print("Server not running or error:", e)

if __name__ == "__main__":
    asyncio.run(main())
