"""
Example of using Observee SDK with local storage
"""
import asyncio
from observee import ObserveeConfig, observee_usage_logger

# Configure to use local storage instead of API
ObserveeConfig.set_mcp_server_name("example-server")
ObserveeConfig.set_local_storage(True, "my_custom_logs.txt")  # Enable local storage

# Example decorated function
@observee_usage_logger
async def my_tool(name: str, value: int):
    """Example tool that does something"""
    return f"Processed {name} with value {value}"

# Example MCP-style tool function
@observee_usage_logger
async def call_tool(name: str, arguments: dict):
    """MCP-style tool caller"""
    return {"result": f"Called {name} with {arguments}"}

async def main():
    # Call the decorated functions
    result1 = await my_tool("test", 42)
    print(f"Result 1: {result1}")
    
    result2 = await call_tool("calculator", {"operation": "add", "a": 5, "b": 3})
    print(f"Result 2: {result2}")
    
    print("\nLogs have been saved to local file. Check 'my_custom_logs.txt'")
    
    # You can also switch back to API mode at runtime
    ObserveeConfig.set_local_storage(False)
    # Now future calls will use the API endpoint

if __name__ == "__main__":
    asyncio.run(main())