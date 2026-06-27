import asyncio
from main import fetch_html_via_mcp, extract_data_with_gemini
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys

async def test_scrape():
    url = "https://www.flipkart.com/apple-iphone-12-pro-graphite-128-gb/p/itm03e5f2595d843"
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-server-fetch-typescript"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Fetching HTML via MCP...")
            html = await fetch_html_via_mcp(session, url)
            if not html:
                print("Failed to fetch HTML")
                return
            
            print(f"HTML length: {len(html)}")
            print("Extracting data...")
            data = extract_data_with_gemini(html, "Flipkart", url)
            print("Final extracted data:", data)

if __name__ == "__main__":
    asyncio.run(test_scrape())
