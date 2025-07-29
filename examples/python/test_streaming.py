#!/usr/bin/env python3
"""
Simple test for streaming functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from observee_agents import chat_with_tools_stream

load_dotenv()

async def stream_example():
    async for chunk in chat_with_tools_stream(
        message="check one last email in my gmail inbox and also check my email from chris",
        provider="anthropic",
        enable_filtering=True,
        observee_api_key=os.getenv("OBSERVEE_API_KEY")
    ):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "final_content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_result":
            print(f"\n🔧 [Tool: {chunk['tool_name']}]")

asyncio.run(stream_example())

if __name__ == "__main__":
    # Check required environment variables
    if not os.getenv("OBSERVEE_API_KEY"):
        print("❌ Please set OBSERVEE_API_KEY environment variable")
        exit(1)
    
    asyncio.run(stream_example()) 