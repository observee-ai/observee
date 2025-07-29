"""Main logging module for the Observee SDK."""

import json
import logging
import time
import asyncio
from typing import Callable, Awaitable, Any, Optional, Union, Dict
from functools import wraps

import httpx

from .constants import API_ENDPOINT
from .configuration import ObserveeConfig
from .models import ToolUsageData, PromptUsageData
from .utils import (
    safe_json_serialize,
    extract_session_id,
    filter_mcp_fields,
    format_response,
    PROMPT_KEYWORDS
)


# Logger instance for this module
logger = logging.getLogger("observe-python-sdk")

# Default timeout for HTTP requests (in seconds)
HTTP_TIMEOUT = 5.0


# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

async def _log_to_file(data: Union[ToolUsageData, PromptUsageData], log_file: str) -> None:
    """
    Log usage data to a local file.
    
    Args:
        data: Usage data to log
        log_file: Path to the log file
    """
    usage_type = "tool" if isinstance(data, ToolUsageData) else "prompt"
    
    try:
        log_entry = {
            "timestamp": time.time(),
            "type": usage_type,
            **data.model_dump()
        }
        
        # Append to file (create if doesn't exist)
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        logger.info(f"{usage_type.title()} usage logged to local file: {log_file}")
    except Exception as file_error:
        logger.error(f"Failed to write to local log file: {str(file_error)}")


async def _log_to_api(data: Union[ToolUsageData, PromptUsageData], api_endpoint: str) -> None:
    """
    Log usage data to the API endpoint.
    
    Args:
        data: Usage data to log
        api_endpoint: API endpoint URL
    """
    usage_type = "tool" if isinstance(data, ToolUsageData) else "prompt"
    
    try:
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        
        # Add API key to header if available
        api_key = ObserveeConfig.get_api_key()
        if api_key:
            headers["X-API-Key"] = api_key
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_endpoint,
                json=data.model_dump(),
                headers=headers,
                timeout=HTTP_TIMEOUT
            )
        
        logger.info(f"{usage_type.title()} usage logged: {json.dumps(data.model_dump())} (status: {response.status_code})")
    except Exception as fetch_error:
        logger.error(f"Failed to send log request: {str(fetch_error)}")


async def log_usage(data: Union[ToolUsageData, PromptUsageData], api_endpoint: str = API_ENDPOINT) -> None:
    """
    Log tool or prompt usage data to either local file or API endpoint.
    
    The destination is determined by the ObserveeConfig settings. If local
    storage is enabled, logs are written to a file. Otherwise, they are
    sent to the configured API endpoint.
    
    Args:
        data: ToolUsageData or PromptUsageData object containing usage information
        api_endpoint: API endpoint for logging (defaults to config setting)
    """
    try:
        usage_type = "tool" if isinstance(data, ToolUsageData) else "prompt"
        identifier = data.tool_name if isinstance(data, ToolUsageData) else data.prompt_name
        logger.debug(f"log_usage called for {usage_type}: {identifier}")
        
        # Check if we should use local storage
        if ObserveeConfig.use_local_storage():
            log_file = ObserveeConfig.get_local_log_file()
            await _log_to_file(data, log_file)
        elif api_endpoint:
            await _log_to_api(data, api_endpoint)
        else:
            logger.info(f"{usage_type.title()} usage logging skipped: No API endpoint configured")
            
    except Exception as error:
        # Log error but don't fail the original operation
        logger.error(f"Exception in log_usage: {str(error)}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_usage_data(
    detected_type: str,
    server_name: str,
    usage_name: str,
    arguments_dict: Optional[Dict[str, Any]],
    kwargs: Dict[str, Any],
    response: Any,
    start_time: Optional[float],
    error: Optional[Exception]
) -> Union[ToolUsageData, PromptUsageData]:
    """
    Build usage data object based on the execution results.
    
    Args:
        detected_type: "tool" or "prompt"
        server_name: MCP server name
        usage_name: Name of the tool/prompt
        arguments_dict: MCP-style arguments dictionary
        kwargs: Function keyword arguments
        response: Function response (None if error occurred)
        start_time: Start timestamp for tools (None for prompts)
        error: Exception if an error occurred
        
    Returns:
        ToolUsageData or PromptUsageData object
    """
    # Extract session ID
    session_id = extract_session_id(kwargs, arguments_dict)
    
    # Determine if we should include input/output data
    include_data = ObserveeConfig.get_api_key() is not None
    
    if detected_type == "tool":
        # Calculate duration
        duration = (time.time() - start_time) * 1000 if start_time else 0
        
        # Build base data
        usage_data_dict = {
            "mcp_server_name": server_name,
            "tool_name": usage_name,
            "duration": duration
        }
        
        if session_id:
            usage_data_dict["session_id"] = session_id
        
        # Add input/output if API key is set
        if include_data:
            # Prepare input data
            if arguments_dict is not None:
                clean_arguments = filter_mcp_fields(arguments_dict)
                tool_input = safe_json_serialize(clean_arguments)
            else:
                tool_input = safe_json_serialize(kwargs)
            usage_data_dict["tool_input"] = tool_input
            
            # Prepare output data
            if error:
                usage_data_dict["tool_response"] = str(error)
            else:
                usage_data_dict["tool_response"] = format_response(response)
        
        return ToolUsageData(**usage_data_dict)
        
    else:  # prompt
        # Build base data
        usage_data_dict = {
            "mcp_server_name": server_name,
            "prompt_name": usage_name
        }
        
        if session_id:
            usage_data_dict["session_id"] = session_id
        
        # Add input/output if API key is set
        if include_data:
            # Prepare input data
            if arguments_dict is not None:
                clean_arguments = filter_mcp_fields(arguments_dict)
                prompt_input = safe_json_serialize(clean_arguments)
            else:
                prompt_input = safe_json_serialize(kwargs)
            usage_data_dict["prompt_input"] = prompt_input
            
            # Prepare output data
            if error:
                usage_data_dict["prompt_response"] = str(error)
            else:
                usage_data_dict["prompt_response"] = format_response(response)
        
        return PromptUsageData(**usage_data_dict)


# ============================================================================
# DECORATOR
# ============================================================================

def observee_usage_logger(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    A unified decorator that logs both tool and prompt usage for MCP functions.
    
    This decorator automatically detects whether to log as a tool or prompt based
    on function name patterns. It captures execution time, inputs, outputs, and
    any errors that occur during execution.
    
    Special handling is provided for MCP-style functions (call_tool, get_prompt)
    where the actual tool/prompt name is passed as the first argument.
    
    Args:
        func: The async function to decorate
        
    Returns:
        Decorated function with usage logging
        
    Example:
        >>> @observee_usage_logger
        ... async def my_tool(arg1: str, arg2: int) -> str:
        ...     return f"Processed {arg1} with {arg2}"
        ... 
        >>> # For MCP-style functions:
        >>> @observee_usage_logger
        ... async def call_tool(name: str, arguments: dict) -> Any:
        ...     # Tool implementation
        ...     return {"result": "success"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Auto-detect type based on function name patterns
        func_name = func.__name__.lower()
        detected_type = "prompt" if any(keyword in func_name for keyword in PROMPT_KEYWORDS) else "tool"
        
        # Extract the actual tool/prompt name
        usage_name = func.__name__
        arguments_dict = None
        
        # Special handling for MCP call_tool and get_prompt patterns
        if func.__name__ == "call_tool" and len(args) >= 2:
            usage_name = args[0]
            arguments_dict = args[1]
        elif func.__name__ == "get_prompt" and len(args) >= 2:
            usage_name = args[0]
            arguments_dict = args[1]
        elif func.__name__ in ["call_tool", "get_prompt"] and "name" in kwargs:
            usage_name = kwargs["name"]
            arguments_dict = kwargs.get("arguments")
        
        # Get MCP server name from global config
        server_name = ObserveeConfig.get_mcp_server_name()
        
        # Start timing for tools
        start_time = time.time() if detected_type == "tool" else None
        
        try:
            # Execute the original function
            response = await func(*args, **kwargs)
            
            # Build usage data
            usage_data = _build_usage_data(
                detected_type=detected_type,
                server_name=server_name,
                usage_name=usage_name,
                arguments_dict=arguments_dict,
                kwargs=kwargs,
                response=response,
                start_time=start_time,
                error=None
            )
            
            # Log asynchronously
            asyncio.create_task(log_usage(usage_data))
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(f"Error in {usage_name}: {str(e)}")
            
            # Build usage data for error case
            usage_data = _build_usage_data(
                detected_type=detected_type,
                server_name=server_name,
                usage_name=usage_name,
                arguments_dict=arguments_dict,
                kwargs=kwargs,
                response=None,
                start_time=start_time,
                error=e
            )
            
            # Log asynchronously
            asyncio.create_task(log_usage(usage_data))
            
            # Re-raise the exception
            raise
    
    return wrapper