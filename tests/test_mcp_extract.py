import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
    )

    print("Starting Puppeteer MCP Server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connection initialized.\n")

            url = "https://example.com"
            print(f"1. Navigating to: {url}")
            
            # Using puppeteer_navigate
            nav_result = await session.call_tool(
                "puppeteer_navigate", 
                arguments={"url": url}
            )
            
            # The result is stored in the content array
            nav_text = nav_result.content[0].text if nav_result.content else "Success"
            print(f"   Navigation Status: {nav_text}")
            
            print("\n2. Extracting text using puppeteer_evaluate...")
            # Simple JavaScript to get the <h1> tag's text
            js_script = "document.querySelector('h1').innerText;"
            
            eval_result = await session.call_tool(
                "puppeteer_evaluate",
                arguments={"script": js_script}
            )
            
            extracted_text = eval_result.content[0].text if eval_result.content else "No text returned"
            print(f"   Extracted <h1>: {extracted_text}\n")
            
            print("Proof of Concept Complete: Navigation and Extraction work perfectly!")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
