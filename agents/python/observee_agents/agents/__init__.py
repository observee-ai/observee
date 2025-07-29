"""
MCP Agent module exports
"""

from .agent import MCPAgent
from .base import BaseAgent, AgentResponse

# Consider switching to the new modular version when ready:
# from .agent_new import MCPAgent

__all__ = [
    "MCPAgent",
    "BaseAgent", 
    "AgentResponse"
]