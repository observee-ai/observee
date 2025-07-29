"""
Unified search module for tool filtering and vector storage
"""

import os
import logging
from typing import Optional, Any

from .base import BaseToolFilter, Tool
from .bm25_filter import BM25Filter

# Lazy imports for optional dependencies
_local_embedding_filter = None
_cloud_filter = None
_vector_store_manager = None

def _get_local_embedding_filter():
    global _local_embedding_filter
    if _local_embedding_filter is None:
        from .local_embedding_filter import LocalEmbeddingFilter
        _local_embedding_filter = LocalEmbeddingFilter
    return _local_embedding_filter

def _get_cloud_filter():
    global _cloud_filter
    if _cloud_filter is None:
        from .cloud_filter import CloudFilter
        _cloud_filter = CloudFilter
    return _cloud_filter

def _get_vector_store_manager():
    global _vector_store_manager
    if _vector_store_manager is None:
        from .cloud_infrastructure import VectorStoreManager
        _vector_store_manager = VectorStoreManager
    return _vector_store_manager

logger = logging.getLogger(__name__)


def create_filter(
    filter_type: str = None,
    vector_store_manager: Optional[Any] = None,
    sync_tools: bool = False,
    **kwargs
) -> BaseToolFilter:
    """
    Create a tool filter instance
    
    Args:
        filter_type: Type of filter to create. Options:
            - "bm25": Fast BM25 keyword search (default, no dependencies)
            - "local_embedding": Local semantic search using fastembed
            - "cloud": Cloud hybrid search using Pinecone (semantic + BM25)
        vector_store_manager: Optional vector store manager for cloud filters
        sync_tools: Whether to clear local caches and force recreation
        **kwargs: Additional arguments for the filter
        
    Returns:
        Tool filter instance
    """
    # Get filter type from environment if not specified
    if not filter_type:
        filter_type = os.getenv("MCP_FILTER_TYPE", "bm25")
    
    filter_type = filter_type.lower()
    
    # Map of available filters
    filter_types = {
        "bm25": BM25Filter,
        "local_embedding": _get_local_embedding_filter,
        "cloud": _get_cloud_filter,
    }
    
    if filter_type not in filter_types:
        logger.warning(f"Unknown filter type: {filter_type}. Using default: bm25")
        filter_type = "bm25"
    
    logger.info(f"Creating {filter_type} filter")
    
    # Get filter class
    filter_entry = filter_types[filter_type]
    # Call lazy loader if needed (but not if it's already a class)
    if callable(filter_entry) and filter_entry not in [BM25Filter]:
        filter_class = filter_entry()
    else:
        filter_class = filter_entry
    
    # Add vector store manager for cloud filter
    if filter_type == "cloud" and vector_store_manager:
        kwargs['vector_store_manager'] = vector_store_manager
    
    # Pass sync_tools to all filter types
    kwargs['sync_tools'] = sync_tools
    
    return filter_class(**kwargs)


__all__ = [
    'BaseToolFilter',
    'Tool',
    'BM25Filter',
    'create_filter'
]

# For backwards compatibility, provide lazy access to optional classes
def __getattr__(name):
    if name == 'LocalEmbeddingFilter':
        return _get_local_embedding_filter()
    elif name == 'CloudFilter':
        return _get_cloud_filter()
    elif name == 'VectorStoreManager':
        return _get_vector_store_manager()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")