"""
Local embedding-based tool filtering using fastembed
"""

import re
import numpy as np
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
import hashlib
import pickle
import os
import logging

from .base import BaseToolFilter, Tool

logger = logging.getLogger(__name__)


COMMON_WORDS = {
    'the', 'and', 'for', 'with', 'from', 'this', 'that', 'will', 'can', 
    'are', 'was', 'were', 'been', 'have', 'has', 'had', 'does', 'did',
    'not', 'but', 'what', 'when', 'where', 'which', 'who', 'how', 'why',
    'all', 'would', 'there', 'their', 'your', 'more', 'other', 'some',
    'into', 'only', 'also', 'than', 'many', 'must', 'should', 'could'
}


class LocalEmbeddingFilter(BaseToolFilter):
    """
    Local embedding-based tool filtering using fastembed.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", sync_tools: bool = False, **kwargs):
        """
        Initialize local embedding filter
        
        Args:
            model_name: FastEmbed model to use
            sync_tools: Whether to clear cache and recreate embeddings
        """
        super().__init__(**kwargs)
        self.model_name = model_name
        self.model = None
        self.embeddings = {}
        self.embedding_cache_file = ".tool_embeddings_cache.pkl"
        self.categories: Dict[str, Set[Tool]] = defaultdict(set)
        
        # Clear cache if sync_tools is True (force fresh embeddings creation)
        if sync_tools and os.path.exists(self.embedding_cache_file):
            try:
                os.remove(self.embedding_cache_file)
                logger.debug("Cleared embedding cache due to sync_tools=True")
            except Exception as e:
                logger.debug(f"Failed to clear embedding cache: {e}")
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize FastEmbed model"""
        try:
            from fastembed import TextEmbedding
            self.model = TextEmbedding(model_name=self.model_name)
            logger.info(f"Initialized FastEmbed with model: {self.model_name}")
        except ImportError:
            logger.warning("fastembed not installed. Install with: pip install fastembed")
            logger.warning("Falling back to keyword-only filtering")
    
    def _extract_metadata(self, tool: Tool):
        """Extract categories and keywords from tool"""
        # Extract from tool name
        name_parts = re.split(r'[_\W]+', tool.name.lower())
        tool.keywords.update(name_parts)
        
        # Extract service/category from prefix
        if '__' in tool.name:
            service = tool.name.split('__')[0].lower()
            tool.categories.add(service)
        
        # Extract keywords from description
        if tool.description:
            desc_words = re.findall(r'\b[a-z]+\b', tool.description.lower())
            meaningful_words = [w for w in desc_words if len(w) > 3 and w not in COMMON_WORDS]
            tool.keywords.update(meaningful_words[:10])
    
    def _create_tool_text(self, tool: Tool) -> str:
        """Create text representation for embedding"""
        return f"{tool.name}: {tool.description or 'No description'}"
    
    def _compute_tools_hash(self) -> str:
        """Compute hash of current tools for cache validation"""
        tool_data = [(t.name, t.description) for t in self.tools]
        return hashlib.md5(str(tool_data).encode()).hexdigest()
    
    def _verify_cache(self, cached_data: Dict[str, Any]) -> bool:
        """Verify if cached embeddings are still valid"""
        current_hash = self._compute_tools_hash()
        return cached_data.get('tool_hash') == current_hash
    
    def _compute_embeddings(self):
        """Compute embeddings for all tools"""
        if not self.model:
            return
        
        # Check cache first
        if os.path.exists(self.embedding_cache_file):
            try:
                with open(self.embedding_cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if self._verify_cache(cached_data):
                        self.embeddings = cached_data['embeddings']
                        logger.debug("Loaded embeddings from cache")
                        return
            except Exception as e:
                logger.debug(f"Cache load failed: {e}")
        
        # Compute new embeddings
        tool_texts = []
        tool_names = []
        
        for tool in self.tools:
            text = self._create_tool_text(tool)
            tool_texts.append(text)
            tool_names.append(tool.name)
        
        if tool_texts:
            # FastEmbed returns a generator, convert to list
            embeddings_list = list(self.model.embed(tool_texts))
            self.embeddings = dict(zip(tool_names, embeddings_list))
            
            # Cache embeddings
            try:
                cache_data = {
                    'embeddings': self.embeddings,
                    'tool_hash': self._compute_tools_hash()
                }
                with open(self.embedding_cache_file, 'wb') as f:
                    pickle.dump(cache_data, f)
                logger.debug("Cached embeddings to disk")
            except Exception as e:
                logger.debug(f"Cache save failed: {e}")
    
    def add_tools(self, tools: List[Any]) -> None:
        """Add tools and compute embeddings"""
        for tool_data in tools:
            # Handle both dict and Tool objects
            if hasattr(tool_data, 'name'):  # Tool object
                tool = Tool(
                    name=tool_data.name,
                    description=tool_data.description or "",
                    server=self._extract_server_from_name(tool_data.name),
                    parameters=tool_data.inputSchema if hasattr(tool_data, 'inputSchema') else {}
                )
            else:  # Dict format
                tool = Tool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    server=tool_data.get("server", self._extract_server_from_name(tool_data.get("name", ""))),
                    parameters=tool_data.get("inputSchema", {})
                )
            
            self._extract_metadata(tool)
            self.tools.append(tool)
            
            # Build categories index
            for category in tool.categories:
                self.categories[category].add(tool)
        
        # Compute embeddings
        self._compute_embeddings()
        
        logger.debug(f"Added {len(self.tools)} tools with embeddings")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def filter_tools(
        self, 
        query: str, 
        max_tools: int = 20, 
        min_score: float = 5.0, 
        context: Dict[str, Any] = None
    ) -> List[Tool]:
        """Filter tools using semantic similarity"""
        if not self.tools:
            return []
        
        scored_tools = []
        
        # Compute query embedding if model available
        query_embedding = None
        if self.model and self.embeddings:
            query_embedding = list(self.model.embed([query]))[0]
        
        query_lower = query.lower()
        query_tokens = set(re.findall(r'\b[a-z]+\b', query_lower)) - COMMON_WORDS
        
        for tool in self.tools:
            score = 0.0
            
            # Semantic similarity score (if available)
            if query_embedding is not None and tool.name in self.embeddings:
                similarity = self._cosine_similarity(query_embedding, self.embeddings[tool.name])
                score += similarity * 100  # Scale to 0-100
            
            # Keyword-based scoring (fallback or additional)
            # Exact matches
            if query_lower in tool.name.lower():
                score += 30.0
            elif any(token in tool.name.lower() for token in query_tokens):
                score += 15.0
            
            # Category match
            for category in tool.categories:
                if category in query_lower:
                    score += 20.0
                    break
            
            # Description relevance
            if tool.description and query_tokens:
                desc_lower = tool.description.lower()
                matching_tokens = sum(1 for token in query_tokens if token in desc_lower)
                score += matching_tokens * 3.0
            
            # Context boosts
            if context:
                if 'previous_tools' in context:
                    for prev_tool in context['previous_tools']:
                        if self._are_tools_related(prev_tool, tool.name):
                            score += 5.0
                
                if 'tool_hints' in context:
                    for hint in context['tool_hints']:
                        hint_lower = hint.lower()
                        if hint_lower in tool.name.lower():
                            score += 10.0
                        elif any(hint_lower in cat for cat in tool.categories):
                            score += 7.0
            
            if score > 0:
                scored_tools.append((score, tool))
        
        # Sort by score
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        
        # Apply threshold
        filtered = [(score, tool) for score, tool in scored_tools if score >= min_score]
        
        # Ensure at least 3 results
        if len(filtered) < 3 and len(scored_tools) >= 3:
            filtered = scored_tools[:3]
        
        # Apply limit
        tools = [tool for _, tool in filtered[:max_tools]]
        
        logger.debug(f"Local embedding filter returned {len(tools)} tools for query: '{query}'")
        if tools:
            logger.debug(f"Top 3 tools: {[t.name for t in tools[:3]]}")
        
        return tools
    
    def _are_tools_related(self, tool1_name: str, tool2_name: str) -> bool:
        """Check if two tools are related"""
        service1 = tool1_name.split('__')[0] if '__' in tool1_name else None
        service2 = tool2_name.split('__')[0] if '__' in tool2_name else None
        return service1 and service2 and service1 == service2
    
    def get_categories(self) -> List[str]:
        """Get all discovered categories"""
        return sorted(list(self.categories.keys()))
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category"""
        return list(self.categories.get(category.lower(), []))