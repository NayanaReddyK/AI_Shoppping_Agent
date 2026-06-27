import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Define the command to start the Puppeteer MCP server.
    # Note: On Windows, npx is typically installed as an npx.cmd script, 
    # so we explicitly call 'npx.cmd' to avoid subprocess FileNotFoundError.
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
    )

    print("Starting Puppeteer MCP Server and establishing connection...")
    
    # 1. Connect to the local MCP server over standard input/output
    async with stdio_client(server_params) as (read, write):
        # 2. Initialize the connection session
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connection initialized successfully!\n")

            print("Fetching available tools from Puppeteer...\n")
            # 3. List available tools
            tools_response = await session.list_tools()
            
            # 4. Print tool names
            print(f"Found {len(tools_response.tools)} tools:")
            print("=" * 50)
            for idx, tool in enumerate(tools_response.tools, 1):
                print(f"{idx}. Tool Name: {tool.name}")
                print(f"   Description: {tool.description}")
                print("-" * 50)

if __name__ == "__main__":
    # Windows specific fix for asyncio if needed in some environments
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    asyncio.run(main())
