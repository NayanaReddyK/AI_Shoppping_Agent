import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys

async def main():
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-server-fetch-typescript"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"TOOL: {t.name}")

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
asyncio.run(main())
