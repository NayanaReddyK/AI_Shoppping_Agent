import asyncio
import sys
import json
import ast
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

            # We use books.toscrape.com - a real website built specifically to mimic 
            # an e-commerce store without aggressive anti-bot captchas that might block our POC.
            url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
            print(f"1. Navigating to: {url}")
            
            await session.call_tool("puppeteer_navigate", arguments={"url": url})
            
            print("2. Extracting Title and Price...")
            
            # JavaScript to extract both title and price and return as a JSON string
            js_script = """
            (() => {
                const title = document.querySelector('h1') ? document.querySelector('h1').innerText : 'Not found';
                const price = document.querySelector('p.price_color') ? document.querySelector('p.price_color').innerText : 'Not found';
                return JSON.stringify({
                    product_title: title,
                    product_price: price,
                    source_url: window.location.href
                });
            })();
            """
            
            eval_result = await session.call_tool(
                "puppeteer_evaluate",
                arguments={"script": js_script}
            )
            
            raw_output = eval_result.content[0].text if eval_result.content else "{}"
            
            # The MCP tool returns a formatted string like: Execution result:\n"{\"product_title\":...}"
            # We parse this string to get the actual JSON back
            json_str = raw_output
            if "Execution result:\n" in raw_output:
                json_str = raw_output.split("Execution result:\n")[1]
                if "\n\nConsole output:" in json_str:
                    json_str = json_str.split("\n\nConsole output:")[0]
                json_str = json_str.strip()
                
            try:
                # ast.literal_eval safely unescapes the stringified JSON string 
                # (e.g. '"{\\"key\\":\\"val\\"}"' -> '{"key":"val"}')
                if json_str.startswith('"') and json_str.endswith('"'):
                    json_str = ast.literal_eval(json_str)
                    
                data = json.loads(json_str)
                print("\n3. Extracted JSON Result:")
                print(json.dumps(data, indent=4))
            except Exception as e:
                print(f"\nFailed to parse JSON. Error: {e}")
                print(f"Raw output was:\n{raw_output}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
