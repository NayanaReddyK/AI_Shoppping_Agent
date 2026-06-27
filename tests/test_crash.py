import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from shopping_agent import run_agentic_loop

async def test():
    print("Starting test...")
    # Mock session
    class MockSession:
        async def call_tool(self, name, arguments):
            class Result:
                content = []
            return Result()
            
    try:
        res = await run_agentic_loop(MockSession(), "https://www.amazon.in/dp/B0CHX1W1XY", "Amazon")
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
