"""Configuration management for the Observee SDK."""

from typing import Optional

from .constants import USE_LOCAL_STORAGE, LOCAL_LOG_FILE


class ObserveeConfig:
    """
    Global configuration for the Observee SDK.
    
    This class manages all configuration settings including:
    - MCP server name (required)
    - API key for enhanced logging features (optional)
    - Storage backend selection (API or local file)
    
    Example:
        >>> from observee import ObserveeConfig
        >>> ObserveeConfig.set_mcp_server_name("my-mcp-server")
        >>> ObserveeConfig.set_api_key("sk-123456")
        >>> ObserveeConfig.set_local_storage(True, "my_logs.txt")
    """
    
    _mcp_server_name: Optional[str] = None
    _api_key: Optional[str] = None
    _use_local_storage: bool = USE_LOCAL_STORAGE
    _local_log_file: str = LOCAL_LOG_FILE

    @classmethod
    def set_mcp_server_name(cls, name: str) -> None:
        """
        Set the global MCP server name.
        
        Args:
            name: The name of the MCP server
            
        Example:
            >>> ObserveeConfig.set_mcp_server_name("my-mcp-server")
        """
        cls._mcp_server_name = name

    @classmethod
    def get_mcp_server_name(cls) -> str:
        """
        Get the global MCP server name.
        
        Returns:
            The configured MCP server name
            
        Raises:
            ValueError: If MCP server name has not been set
            
        Example:
            >>> server_name = ObserveeConfig.get_mcp_server_name()
        """
        if cls._mcp_server_name is None:
            raise ValueError("MCP server name not set. Call set_mcp_server_name() first.")
        return cls._mcp_server_name
        
    @classmethod
    def set_api_key(cls, api_key: str) -> None:
        """
        Set the global API key for enhanced logging features.
        
        When an API key is set, tool/prompt inputs and outputs will be included
        in the logs. Without an API key, only metadata is logged.
        
        Args:
            api_key: The API key to use
            
        Example:
            >>> ObserveeConfig.set_api_key("sk-123456789")
        """
        cls._api_key = api_key
        
    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """
        Get the global API key if set.
        
        Returns:
            The configured API key or None if not set
        """
        return cls._api_key
    
    @classmethod
    def set_local_storage(cls, use_local: bool, log_file: Optional[str] = None) -> None:
        """
        Configure local storage settings.
        
        Args:
            use_local: Whether to use local file storage instead of API
            log_file: Optional custom log file path (defaults to config setting)
            
        Example:
            >>> # Enable local storage with default file
            >>> ObserveeConfig.set_local_storage(True)
            >>> 
            >>> # Enable local storage with custom file
            >>> ObserveeConfig.set_local_storage(True, "my_custom_logs.txt")
        """
        cls._use_local_storage = use_local
        if log_file:
            cls._local_log_file = log_file
            
    @classmethod
    def use_local_storage(cls) -> bool:
        """
        Check if local storage is enabled.
        
        Returns:
            True if local storage is enabled, False otherwise
        """
        return cls._use_local_storage
        
    @classmethod
    def get_local_log_file(cls) -> str:
        """
        Get the local log file path.
        
        Returns:
            The path to the local log file
        """
        return cls._local_log_file