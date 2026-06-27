import asyncio
import sys
import os
import base64
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    # 1 & 2. Configuring Puppeteer environment variables
    env = os.environ.copy()
    # Force Puppeteer to use your real local Chrome instead of the bundled Chromium
    env["PUPPETEER_EXECUTABLE_PATH"] = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    # Note: The official MCP server hardcodes headless: true. 
    # Passing HEADLESS=false here works for community stealth plugins but is ignored by the standard server.
    env["HEADLESS"] = "false" 
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
        env=env
    )

    url = "https://www.amazon.in/dp/B0CX5BMV2F"
    
    print("Starting Puppeteer MCP Server (Bot Diagnosis Mode)...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connection initialized.\n")

            print(f"1. Navigating to Amazon: {url}")
            await session.call_tool("puppeteer_navigate", arguments={"url": url})
            
            print("2. Capturing screenshot for bot-diagnosis...")
            # 5. Capturing screenshots via MCP
            screenshot_result = await session.call_tool(
                "puppeteer_screenshot",
                arguments={"name": "amazon_test", "width": 1280, "height": 800}
            )
            
            # The MCP SDK returns ImageContent for screenshots
            content = screenshot_result.content[0]
            img_data = ""
            
            if hasattr(content, 'data'):
                img_data = content.data # Base64 string
            elif hasattr(content, 'text'):
                img_data = content.text
                
            # Clean up Data URI prefix if present
            if img_data.startswith("data:image"):
                img_data = img_data.split(",")[1]
                
            # Fix Incorrect padding issue for Python base64 decoder
            img_data += "=" * ((4 - len(img_data) % 4) % 4)
                
            try:
                # Save the image locally to inspect what Amazon actually served us
                with open("amazon_bot_diagnosis.png", "wb") as f:
                    f.write(base64.b64decode(img_data))
                print("   Saved screenshot to 'amazon_bot_diagnosis.png' in your project folder.")
                print("   --> OPEN THIS IMAGE to see the CAPTCHA or blocking page!")
            except Exception as e:
                print(f"   Failed to save screenshot: {e}")

            print("\n3. Attempting Title Extraction...")
            js_script = "document.querySelector('#productTitle')?.innerText || 'Title not found';"
            eval_result = await session.call_tool("puppeteer_evaluate", arguments={"script": js_script})
            
            raw_text = eval_result.content[0].text if eval_result.content else ""
            if "Execution result:\n" in raw_text:
                raw_text = raw_text.split("Execution result:\n")[1]
                if "\n\nConsole output:" in raw_text:
                    raw_text = raw_text.split("\n\nConsole output:")[0]
                    
            print(f"   Extracted Result: {raw_text.strip()}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
