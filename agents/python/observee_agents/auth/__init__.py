"""
Observee Authentication Module

This module provides authentication functionality for the Observee MCP Agent SDK,
including OAuth flows for various services through the mcpauth API.
"""

from .mcpauth import (
    call_mcpauth_login,
    get_available_servers,
    get_servers_by_client,
    McpAuthClient,
    McpAuthError
)

__all__ = [
    "call_mcpauth_login",
    "get_available_servers",
    "get_servers_by_client",
    "McpAuthClient",
    "McpAuthError"
] 