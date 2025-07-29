#!/usr/bin/env python3
"""
Simple test for custom tools functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from observee_agents import chat_with_tools_stream

load_dotenv()

# Define custom tool handler
async def custom_tool_handler(tool_name: str, tool_input: dict) -> str:
    """Simple custom tool implementations"""
    if tool_name == "add_numbers":
        return str(tool_input.get("a", 0) + tool_input.get("b", 0))
    elif tool_name == "multiply_numbers":
        return str(tool_input.get("a", 0) * tool_input.get("b", 0))
    elif tool_name == "get_time":
        from datetime import datetime
        return datetime.now().strftime("%I:%M %p")
    else:
        return f"Unknown tool: {tool_name}"

# Define custom tools in OpenAI format
custom_tools = [
    {
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "Add two numbers together",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "multiply_numbers",
            "description": "Multiply two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

async def custom_tools_example():
    async for chunk in chat_with_tools_stream(
        message="what tools do u have",
        provider="gemini",
        enable_filtering=True,  # Disable filtering to only use custom tools
        custom_tools=custom_tools,
        custom_tool_handler=custom_tool_handler
    ):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "final_content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_result":
            print(f"\n🔧 [Tool: {chunk['tool_name']} = {chunk['result']}]")
        elif chunk["type"] == "phase":
            print(f"\n📍 [{chunk['phase'].replace('_', ' ').title()}]")

if __name__ == "__main__":
    print("🧮 Custom Tools Test\n")
    asyncio.run(custom_tools_example())