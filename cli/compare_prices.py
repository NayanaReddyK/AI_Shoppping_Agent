import asyncio
import sys
import json
import ast
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def extract_from_url(session, url):
    print(f"\nNavigating to: {url}")
    await session.call_tool("puppeteer_navigate", arguments={"url": url})
    
    # We use a JavaScript snippet that dynamically adjusts its CSS selectors
    # based on which store we are currently browsing.
    js_script = """
    (() => {
        let title = 'Not found';
        let price = 'Not found';
        let store = 'Unknown';
        const hostname = window.location.hostname;
        
        if (hostname.includes('amazon')) {
            store = 'Amazon';
            title = document.querySelector('#productTitle')?.innerText?.trim() || 'Not found';
            price = document.querySelector('.a-price .a-offscreen')?.innerText?.trim() || 'Not found';
        } else if (hostname.includes('flipkart')) {
            store = 'Flipkart';
            // Flipkart classes change often, we try a few known ones
            title = document.querySelector('.VU-Tz5, .B_NuCI, span.B_NuCI')?.innerText?.trim() || 'Not found';
            price = document.querySelector('.Nx9bqj, ._30jeq3, div._30jeq3')?.innerText?.trim() || 'Not found';
        } else if (hostname.includes('croma')) {
            store = 'Croma';
            title = document.querySelector('h1')?.innerText?.trim() || 'Not found';
            price = document.querySelector('.amount, .pdp-price')?.innerText?.trim() || 'Not found';
        } else {
            // Generic fallback for other stores
            store = hostname;
            title = document.querySelector('h1')?.innerText?.trim() || 'Not found';
            price = document.querySelector('.price, .amount, [class*="price"]')?.innerText?.trim() || 'Not found';
        }
        
        return JSON.stringify({
            store: store,
            title: title,
            price: price
        });
    })();
    """
    
    print(f"Extracting data...")
    eval_result = await session.call_tool("puppeteer_evaluate", arguments={"script": js_script})
    
    raw_output = eval_result.content[0].text if eval_result.content else "{}"
    
    json_str = raw_output
    if "Execution result:\n" in raw_output:
        json_str = raw_output.split("Execution result:\n")[1]
        if "\n\nConsole output:" in json_str:
            json_str = json_str.split("\n\nConsole output:")[0]
        json_str = json_str.strip()
        
    try:
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = ast.literal_eval(json_str)
        return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON from {url}: {e}")
        return {"store": url, "title": "Error", "price": "Error"}

async def main():
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
    )

    # Sample URLs for comparison.
    # Note: Amazon and Flipkart often block headless browsers or require captchas.
    # If the prices show as "Not found", it's usually because a captcha was served instead of the product page!
    urls = [
        "https://www.amazon.in/dp/B0CX5BMV2F", # Sample Amazon URL
        "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4" # Sample Flipkart URL
    ]

    print("Starting Puppeteer MCP Server for Price Comparison...")
    
    results = []
    product_name = None
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            for url in urls:
                data = await extract_from_url(session, url)
                if data:
                    # Capture product name from the first successful extraction
                    if not product_name and data.get("title") not in ["Not found", "Error"]:
                        product_name = data.get("title")
                    
                    results.append({
                        "store": data.get("store"),
                        "price": data.get("price")
                    })
    
    final_output = {
        "product": product_name or "Unknown Product (Extraction Blocked/Failed)",
        "stores": results
    }
    
    print("\n" + "="*50)
    print("FINAL STRUCTURED JSON:")
    print("="*50)
    print(json.dumps(final_output, indent=4))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
