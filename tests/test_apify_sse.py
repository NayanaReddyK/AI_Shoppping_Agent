import asyncio
import sys
import os
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    apify_token = os.environ.get("APIFY_TOKEN")
    if not apify_token:
        print("Error: APIFY_TOKEN environment variable is not set.")
        print("Please set it: $env:APIFY_TOKEN='your_apify_api_token'")
        return

    # 1. The SSE endpoint provided by Apify for remote MCP execution
    mcp_url = "https://mcp.apify.com/?tools=actors,docs,easyapi/flipkart-product-scraper"
    
    # We pass the Apify API token via the Authorization header (standard for remote MCP servers)
    # Some implementations may also accept it in the URL: f"{mcp_url}&token={apify_token}"
    headers = {
        "Authorization": f"Bearer {apify_token}"
    }

    print("1. Connecting to Apify MCP Server via SSE...")
    async with sse_client(url=mcp_url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connection initialized successfully!\n")
            
            # 2. Discover available tools
            print("2. Discovering available tools from Apify...")
            tools_response = await session.list_tools()
            
            target_tool = None
            print("Tools Found:")
            for t in tools_response.tools:
                print(f" - {t.name}: {t.description}")
                # Dynamically find the flipkart tool based on its name
                if "flipkart" in t.name.lower():
                    target_tool = t.name
            
            if not target_tool:
                print("\nError: Could not find the Flipkart scraper tool in the returned list.")
                return
                
            # 3 & 4. Run the Flipkart Product Scraper actor
            product_url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"
            print(f"\n3. Executing Tool: '{target_tool}' for URL: {product_url}")
            print("Please wait... Cloud execution on Apify can take 10-30 seconds...")
            
            # The tool usually expects the standard Apify Actor input schema.
            # We pass the arguments required by easyapi/flipkart-product-scraper.
            try:
                result = await session.call_tool(
                    target_tool,
                    arguments={
                        "input": {
                            "startUrls": [{"url": product_url}]
                        }
                    }
                )
                
                # 5. Print the result
                raw_output = result.content[0].text if result.content else "{}"
                print("\n5. Extraction Result (Structured JSON):")
                
                try:
                    parsed_json = json.loads(raw_output)
                    print(json.dumps(parsed_json, indent=4))
                except json.JSONDecodeError:
                    print(raw_output)
                    
            except Exception as e:
                print(f"\nError executing tool: {e}")
                print("Note: If the tool argument schema is incorrect, you may need to adjust the 'arguments' dictionary based on the tool's expected input schema.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
