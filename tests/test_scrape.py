import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_scrape():
    # Import the actual functions
    from shopping_agent import fetch_html_via_mcp
    from main import extract_data_with_groq
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import sys
    import urllib.parse
    
    url = "https://in.jbl.com/JBLC100SIUBLKE.html"
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(command=command, args=["-y", "mcp-server-fetch-typescript"])
    
    print("Starting MCP fetch...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Test with render=true
                scraper_url = f"http://api.scraperapi.com?api_key=f618ee3965566ce7dfa1852f25f0040a&url={urllib.parse.quote(url)}&render=true"
                result = await session.call_tool("get_raw_text", arguments={"url": scraper_url})
                html = result.content[0].text if result.content else ""
                
                if not html:
                    print("Failed to fetch HTML!")
                    return
                print("HTML fetched successfully (length:", len(html), ")")
                data = await extract_data_with_groq(html, "Sangeetha", url)
                print("Extracted Data:", data)
    except Exception as e:
        print("Scrape failed:", e)

if __name__ == "__main__":
    asyncio.run(test_scrape())
