"""
BM25-based tool filtering using bm25s library - fast and efficient
"""

import re
import bm25s
import numpy as np
import pickle
import os
import hashlib
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
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


class BM25Filter(BaseToolFilter):
    """
    BM25-based tool filtering using bm25s.
    Fast, efficient, no external API dependencies.
    This is the default filter.
    """
    
    def __init__(self, use_cache: bool = True, sync_tools: bool = False, **kwargs):
        """Initialize BM25 filter"""
        super().__init__(**kwargs)
        self.bm25 = None
        self.corpus_tokens = []
        self.categories: Dict[str, Set[Tool]] = defaultdict(set)
        self.tool_indices = {}  # Map tool name to corpus index
        self.use_cache = use_cache
        self.cache_file = ".bm25_index_cache.pkl"
        
        # Clear cache if sync_tools is True (force fresh index creation)
        if sync_tools and os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
                logger.debug("Cleared BM25 cache due to sync_tools=True")
            except Exception as e:
                logger.debug(f"Failed to clear BM25 cache: {e}")
    
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
        
        # Extract from parameter names
        if tool.parameters and isinstance(tool.parameters, dict):
            self._extract_param_keywords(tool, tool.parameters)
    
    def _extract_param_keywords(self, tool: Tool, schema: Dict[str, Any], depth: int = 0):
        """Recursively extract keywords from parameter schema"""
        if depth > 2:
            return
        
        if 'properties' in schema:
            for prop_name, prop_schema in schema.get('properties', {}).items():
                tool.keywords.add(prop_name.lower())
                if isinstance(prop_schema, dict) and 'description' in prop_schema:
                    desc_words = re.findall(r'\b[a-z]+\b', prop_schema['description'].lower())
                    tool.keywords.update(w for w in desc_words if len(w) > 3 and w not in COMMON_WORDS)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25"""
        # Simple tokenization - lowercase and split
        tokens = re.findall(r'\b[a-z]+\b', text.lower())
        # Remove common words and short tokens
        return [t for t in tokens if t not in COMMON_WORDS and len(t) > 2]
    
    def _create_tool_document(self, tool: Tool) -> str:
        """Create searchable document from tool"""
        # Combine all searchable text with weights
        parts = [
            tool.name,  # Name is most important
            tool.name.replace('_', ' ').replace('__', ' '),  # Split name parts
            tool.description or "",
            " ".join(tool.categories) * 2,  # Boost categories
            " ".join(list(tool.keywords)[:20])  # Limit keywords
        ]
        return " ".join(parts)
    
    def _compute_tools_hash(self) -> str:
        """Compute hash of current tools for cache validation"""
        tool_data = [(t.name, t.description) for t in self.tools]
        return hashlib.md5(str(tool_data).encode()).hexdigest()
    
    def _save_cache(self):
        """Save BM25 index and related data to cache"""
        if not self.use_cache:
            return
        
        try:
            cache_data = {
                'tool_hash': self._compute_tools_hash(),
                'corpus_tokens': self.corpus_tokens,
                'tool_indices': self.tool_indices,
                'tools': self.tools,
                'categories': dict(self.categories)
            }
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.debug("Saved BM25 cache")
        except Exception as e:
            logger.debug(f"Failed to save cache: {e}")
    
    def _load_cache(self) -> bool:
        """Load BM25 index from cache if valid"""
        if not self.use_cache or not os.path.exists(self.cache_file):
            return False
        
        try:
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Verify cache is still valid
            if cache_data.get('tool_hash') != self._compute_tools_hash():
                logger.debug("Cache invalidated due to tool changes")
                return False
            
            # Restore data
            self.corpus_tokens = cache_data['corpus_tokens']
            self.tool_indices = cache_data['tool_indices']
            self.tools = cache_data['tools']
            self.categories = defaultdict(set, cache_data['categories'])
            
            # Rebuild BM25 index
            self.bm25 = bm25s.BM25(k1=1.5, b=0.75)
            self.bm25.index(self.corpus_tokens)
            
            logger.debug("Loaded BM25 index from cache")
            return True
            
        except Exception as e:
            logger.debug(f"Failed to load cache: {e}")
            return False
    
    def add_tools(self, tools: List[Any]) -> None:
        """Add tools and build BM25 index"""
        # Process tools first to enable cache checking
        for tool_data in tools:
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
        
        # Try to load from cache
        if self._load_cache():
            return
        
        # Build index from scratch
        corpus = []
        
        for idx, tool in enumerate(self.tools):
            # Build categories index
            for category in tool.categories:
                self.categories[category].add(tool)
            
            # Create document and tokenize
            doc = self._create_tool_document(tool)
            tokens = self._tokenize(doc)
            
            # Debug logging
            if idx < 3:  # Log first 3 tools
                logger.debug(f"Tool {idx}: {tool.name}")
                logger.debug(f"  Doc: {doc[:100]}...")
                logger.debug(f"  Tokens: {tokens[:10]}...")
            
            corpus.append(tokens)
            
            # Store index mapping
            self.tool_indices[tool.name] = idx
        
        # Build BM25 index with bm25s
        self.corpus_tokens = corpus
        
        # Check if we have any valid documents
        non_empty_docs = [doc for doc in corpus if doc]
        if not non_empty_docs:
            logger.warning("No valid documents in corpus! All documents are empty.")
            # Create a dummy corpus to avoid the error
            corpus = [['dummy']]
        
        self.bm25 = bm25s.BM25(k1=1.5, b=0.75)
        self.bm25.index(corpus)
        
        logger.debug(f"BM25 index built with {len(self.tools)} tools")
        logger.debug(f"Corpus has {len(corpus)} documents")
        if corpus:
            logger.debug(f"First doc has {len(corpus[0])} tokens: {corpus[0][:5]}...")
        
        # Save cache for next time
        self._save_cache()
    
    async def filter_tools(
        self, 
        query: str, 
        max_tools: int = 20, 
        min_score: float = 5.0, 
        context: Dict[str, Any] = None
    ) -> List[Tool]:
        """Filter tools using BM25 ranking"""
        if not self.bm25 or not self.tools:
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        logger.debug(f"Query tokens: {query_tokens}")
        
        # Get BM25 scores
        # bm25s expects a list of queries (batch format)
        # and returns (results, scores) tuple
        indices, scores = self.bm25.retrieve(
            [query_tokens],  # Wrap in list for batch format
            k=len(self.tools)  # Get all scores
        )
        
        # Combine with additional scoring
        query_lower = query.lower()
        scored_tools = []
        
        for idx, bm25_score in zip(indices[0], scores[0]):
            if idx >= len(self.tools):
                continue
                
            tool = self.tools[idx]
            
            # Start with BM25 score (scale it up)
            total_score = float(bm25_score) * 10
            
            # Add boosts for exact matches
            if query_lower in tool.name.lower():
                total_score += 50.0
            elif any(token in tool.name.lower() for token in query_tokens):
                total_score += 20.0
            
            # Category match boost
            for category in tool.categories:
                if category in query_lower:
                    total_score += 30.0
                    break
            
            # Context boosts
            if context:
                if 'previous_tools' in context:
                    for prev_tool in context['previous_tools']:
                        if self._are_tools_related(prev_tool, tool.name):
                            total_score += 10.0
                
                if 'tool_hints' in context:
                    for hint in context['tool_hints']:
                        hint_lower = hint.lower()
                        if hint_lower in tool.name.lower():
                            total_score += 20.0
                        elif any(hint_lower in cat for cat in tool.categories):
                            total_score += 15.0
            
            if total_score > 0:
                scored_tools.append((total_score, tool))
        
        # Sort by total score
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        
        # Apply threshold
        filtered = [(score, tool) for score, tool in scored_tools if score >= min_score]
        
        # Ensure at least 3 results if available
        if len(filtered) < 3 and len(scored_tools) >= 3:
            filtered = scored_tools[:3]
        
        # Apply diversity and limit
        if len(filtered) > max_tools:
            tools = self._apply_diversity(filtered, max_tools)
        else:
            tools = [tool for _, tool in filtered[:max_tools]]
        
        logger.debug(f"BM25 filter returned {len(tools)} tools for query: '{query}'")
        if tools:
            logger.debug(f"Top 3 tools: {[t.name for t in tools[:3]]}")
        
        return tools
    
    def _are_tools_related(self, tool1_name: str, tool2_name: str) -> bool:
        """Check if two tools are related"""
        service1 = tool1_name.split('__')[0] if '__' in tool1_name else None
        service2 = tool2_name.split('__')[0] if '__' in tool2_name else None
        return service1 and service2 and service1 == service2
    
    def _apply_diversity(self, scored_tools: List[Tuple[float, Tool]], max_tools: int) -> List[Tool]:
        """Ensure diversity in results"""
        selected = []
        category_counts = defaultdict(int)
        max_per_category = max(2, max_tools // 3)
        
        for score, tool in scored_tools:
            tool_categories = list(tool.categories) if tool.categories else ['default']
            can_add = all(category_counts[cat] < max_per_category for cat in tool_categories)
            
            if can_add:
                selected.append(tool)
                for cat in tool_categories:
                    category_counts[cat] += 1
                
                if len(selected) >= max_tools:
                    break
        
        return selected
    
    def get_categories(self) -> List[str]:
        """Get all discovered categories"""
        return sorted(list(self.categories.keys()))
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category"""
        return list(self.categories.get(category.lower(), []))