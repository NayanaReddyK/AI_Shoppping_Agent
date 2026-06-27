import asyncio
import os
import urllib.parse
import sys
from dotenv import load_dotenv

# Dynamically resolve root path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(override=True)

async def test_groq_extraction():
    from skills.scraper_skill import extract_data_with_groq
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    
    url = "https://www.amazon.in/Noise-Smartwatch-Calling-Tracking-Monitoring/dp/B0CQ4K8J3R?source=ps-sl-shoppingads-lpcontext&ref_=fplfs&smid=AJ6SIZC8YQDZX&th=1"
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(command=command, args=["-y", "mcp-server-fetch-typescript"])
    
    print("Fetching HTML via ScraperAPI...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            scraper_url = f"http://api.scraperapi.com?api_key=f618ee3965566ce7dfa1852f25f0040a&url={urllib.parse.quote(url)}&render=false"
            result = await session.call_tool("get_raw_text", arguments={"url": scraper_url})
            html = result.content[0].text if result.content else ""
            
            if not html:
                print("Failed to fetch HTML!")
                return
            
            print("HTML fetched. Running Groq extraction...")
            data = await extract_data_with_groq(html, "Amazon", url)
            with open("debug/test_groq_output.txt", "w", encoding="utf-8") as f:
                f.write(f"Extraction result: {data}")
            print("Done. Check debug/test_groq_output.txt")

if __name__ == "__main__":
    asyncio.run(test_groq_extraction())
