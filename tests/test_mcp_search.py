import asyncio
import sys
import os
import json
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        print("Error: BRAVE_API_KEY environment variable is not set.")
        print("Please set it before running the script.")
        print("Example (Windows PowerShell):")
        print("$env:BRAVE_API_KEY='your_api_key_here'; python test_mcp_search.py")
        sys.exit(1)

    command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    # Pass the current environment so the MCP server gets the API key
    env = os.environ.copy()
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env=env
    )

    product_name = "Samsung Galaxy S25"
    
    # We append "buy online price" to narrow down to shopping pages
    search_query = f"{product_name} buy online price"

    print("Starting Brave Search MCP Server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connection initialized.\n")
            
            print(f"1. Searching for: '{search_query}'")
            
            # The Brave Search MCP exposes the 'brave_web_search' tool
            search_result = await session.call_tool(
                "brave_web_search",
                arguments={"query": search_query}
            )
            
            raw_text = search_result.content[0].text if search_result.content else ""
            
            print("\n2. Extracting URLs from Search Results...")
            
            # The MCP server might return raw JSON or Markdown.
            # To ensure we just get the URLs regardless of format, we'll use regex.
            urls = re.findall(r'(https?://[^\s)\]"\']+)', raw_text)
            
            # Deduplicate while preserving order
            unique_urls = list(dict.fromkeys(urls))
            
            # Filter out irrelevant URLs (like brave internal links if any)
            product_urls = [u for u in unique_urls if "brave.com" not in u]
            
            # Build the structured JSON output
            output_json = {
                "product_name": product_name,
                "search_query": search_query,
                "top_urls": product_urls[:5], # Take top 5 results
            }
            
            print("\n3. Final Structured JSON:")
            print(json.dumps(output_json, indent=4))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
