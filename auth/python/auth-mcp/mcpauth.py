"""
McpAuth Client for Observee MCP Agent SDK

This module provides OAuth authentication flows for various services
through the Observee mcpauth API with built-in .env support.
"""

import json
import os
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class McpAuthError(Exception):
    """Custom exception for mcpauth-related errors"""
    pass


class McpAuthClient:
    """
    Client for interacting with the Observee mcpauth API.
    
    This client handles OAuth flows for various services and automatically
    loads configuration from environment variables.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the McpAuth client.
        
        Args:
            api_key: Observee API key (defaults to OBSERVEE_API_KEY env var)
            base_url: Base URL for mcpauth API (defaults to https://mcpauth.observee.ai)
        """
        self.api_key = api_key or os.getenv("OBSERVEE_API_KEY")
        self.base_url = base_url or "https://mcpauth.observee.ai"
        
        if not self.api_key:
            raise McpAuthError(
                "No API key provided. Set OBSERVEE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def get_available_servers(self) -> Dict[str, Any]:
        """
        Get all available authentication servers from the mcpauth API.
        
        Returns:
            Dict containing the JSON response with available servers
            
        Raises:
            McpAuthError: If the request fails or returns an error
        """
        url = f"{self.base_url}/supported_servers"
        body = {"OBSERVEE_API_KEY": self.api_key}
        
        try:
            response = self.session.post(url, json=body)
            json_response = response.json()
            
            # Add metadata
            json_response["_status_code"] = response.status_code
            json_response["_url_called"] = url
            
            if response.status_code != 200:
                raise McpAuthError(f"API request failed: {json_response.get('error', 'Unknown error')}")
            
            return json_response
            
        except requests.RequestException as e:
            raise McpAuthError(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise McpAuthError(f"Invalid JSON response from server: {response.text}")
    
    def start_auth_flow(
        self,
        auth_server: str,
        client_id: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start an OAuth flow for the specified authentication server.
        
        Args:
            auth_server: The service to authenticate with (e.g., 'gmail', 'slack', 'atlassian')
            client_id: Optional client identifier
            additional_params: Optional additional parameters for specific auth servers
        
        Returns:
            Dict containing the JSON response from mcpauth, including the OAuth URL
            
        Raises:
            McpAuthError: If the request fails or returns an error
        """
        url = f"{self.base_url}/enterprise/{auth_server}/start"
        
        # Prepare request body
        body = {"OBSERVEE_API_KEY": self.api_key}
        
        # Add additional parameters to the body
        if additional_params:
            body.update(additional_params)
        
        # Prepare query parameters
        params = {}
        if client_id:
            params["client_id"] = client_id
        
        try:
            response = self.session.post(url, json=body, params=params)
            json_response = response.json()
            
            # Add metadata
            json_response["_status_code"] = response.status_code
            json_response["_url_called"] = url
            
            if response.status_code != 200:
                raise McpAuthError(f"Auth flow failed: {json_response.get('error', 'Unknown error')}")
            
            return json_response
            
        except requests.RequestException as e:
            raise McpAuthError(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise McpAuthError(f"Invalid JSON response from server: {response.text}")
    
    def list_supported_servers(self) -> List[str]:
        """
        Get a simple list of supported authentication servers.
        
        Returns:
            List of supported server names
            
        Raises:
            McpAuthError: If the request fails
        """
        response = self.get_available_servers()
        return response.get("supported_servers", [])
    
    def get_servers_by_client(self, client_id: str) -> Dict[str, Any]:
        """
        Get list of servers associated with a specific client ID.
        
        Args:
            client_id: The client identifier to get servers for
            
        Returns:
            Dict containing:
                - client_id: The client ID
                - servers: List of server names
                - total_count: Total number of servers
                
        Raises:
            McpAuthError: If the request fails or returns an error
        """
        url = f"{self.base_url}/servers_by_client"
        body = {
            "OBSERVEE_API_KEY": self.api_key,
            "client_id": client_id
        }
        
        try:
            response = self.session.post(url, json=body)
            json_response = response.json()
            
            # Add metadata
            json_response["_status_code"] = response.status_code
            json_response["_url_called"] = url
            
            if response.status_code != 200:
                raise McpAuthError(f"API request failed: {json_response.get('error', 'Unknown error')}")
            
            return json_response
            
        except requests.RequestException as e:
            raise McpAuthError(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise McpAuthError(f"Invalid JSON response from server: {response.text}")


# Convenience functions for backward compatibility and ease of use
def call_mcpauth_login(
    api_key: Optional[str] = None,
    auth_server: str = "gmail",
    client_id: Optional[str] = None,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Call the mcpauth URL to start a login flow and return the JSON response.
    
    Args:
        api_key: Your Observee API key (defaults to OBSERVEE_API_KEY env var)
        auth_server: The service to authenticate with (e.g., 'gmail', 'slack', 'atlassian')
        client_id: Optional client identifier
        additional_params: Optional additional parameters for specific auth servers
    
    Returns:
        Dict containing the JSON response from mcpauth
        
    Raises:
        McpAuthError: If the request fails or returns an error
    """
    client = McpAuthClient(api_key=api_key)
    return client.start_auth_flow(auth_server, client_id, additional_params)


def get_available_servers(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all available authentication servers from the mcpauth API.
    
    Args:
        api_key: Your Observee API key (defaults to OBSERVEE_API_KEY env var)
    
    Returns:
        Dict containing the JSON response with available servers
        
    Raises:
        McpAuthError: If the request fails or returns an error
    """
    client = McpAuthClient(api_key=api_key)
    return client.get_available_servers()


def get_servers_by_client(client_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get list of servers associated with a specific client ID.
    
    Args:
        client_id: The client identifier to get servers for
        api_key: Your Observee API key (defaults to OBSERVEE_API_KEY env var)
        
    Returns:
        Dict containing:
            - client_id: The client ID
            - servers: List of server names
            - total_count: Total number of servers
            
    Raises:
        McpAuthError: If the request fails or returns an error
    """
    client = McpAuthClient(api_key=api_key)
    return client.get_servers_by_client(client_id)


# Predefined list of commonly supported servers (can be updated via API call)
SUPPORTED_SERVERS = [
    "atlassian", "gmail", "gcal", "gdocs", "gdrive", "gsheets", 
    "gslides", "slack", "notion", "linear", "asana", "outlook", 
    "onedrive", "onenote", "supabase", "airtable", "discord"
] 