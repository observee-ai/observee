"""
Unified cloud infrastructure for vector search.
Combines embeddings, Pinecone store, and manager functionality.
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

import openai
from openai import AsyncOpenAI
import pinecone
from pinecone import Pinecone, ServerlessSpec
import bm25s
import numpy as np

logger = logging.getLogger(__name__)
load_dotenv()


# ============= Embeddings =============

class OpenAIEmbeddings:
    """Handle OpenAI embeddings for tools"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-large",
        dimension: int = 3072
    ):
        """
        Initialize OpenAI embeddings
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Embedding model to use
            dimension: Output dimension (3072 for text-embedding-3-large)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        self.dimension = dimension
        
        logger.debug(f"Initialized OpenAI embeddings with model: {model}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimension
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def embed_tool(self, tool_data: Dict[str, Any]) -> List[float]:
        """
        Generate embedding for a tool
        
        Args:
            tool_data: Tool data with name, description, etc.
            
        Returns:
            Embedding vector
        """
        # Create rich text representation
        name = tool_data.get("name", "")
        description = tool_data.get("description", "")
        category = tool_data.get("category", "")
        
        # Extract parameter names
        input_schema = tool_data.get("inputSchema", {})
        param_names = list(input_schema.get("properties", {}).keys())
        
        # Combine into embedding text
        embedding_text = f"{name} {description} {category} {' '.join(param_names)}"
        
        return await self.embed_text(embedding_text)


# ============= Pinecone Store =============

class PineconeVectorStore:
    """Handle Pinecone vector storage for MCP tools"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: str = "mcp-tools-hybrid",
        environment: str = "us-east-1",
        dimension: int = 3072
    ):
        """
        Initialize Pinecone vector store
        
        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            environment: Pinecone environment/region
            dimension: Vector dimension (must match embedding model)
        """
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("Pinecone API key required. Set PINECONE_API_KEY env var or pass api_key")
        
        self.index_name = index_name
        self.environment = environment
        self.dimension = dimension
        self.pc = None
        self.index = None
        self.initialized = False
        
        # BM25 for hybrid search
        self.bm25 = None
        self.tool_corpus = []  # Store tool texts for BM25
        self.corpus_tokens = []  # Store tokenized corpus
        self._bm25_fitted = False  # Track if BM25 is already fitted
    
    async def initialize(self) -> None:
        """Initialize Pinecone client and create index if needed"""
        if self.initialized:
            return
        
        try:
            # Initialize Pinecone
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes.indexes]
            
            if self.index_name not in index_names:
                # Create index with hybrid search support
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="dotproduct",  # Required for hybrid search
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=self.environment
                    )
                )
                
                # Wait for index to be ready
                import time
                while not self.pc.describe_index(self.index_name).status.ready:
                    time.sleep(1)
            
            # Get index
            self.index = self.pc.Index(self.index_name)
            
            # Wait for index to be ready
            stats = self.index.describe_index_stats()
            logger.debug(f"Pinecone index stats: {stats}")
            
            # Initialize BM25 for hybrid search
            self.bm25 = bm25s.BM25(k1=1.5, b=0.75)
            await self._load_corpus_for_bm25()
            
            self.initialized = True
            logger.info(f"Initialized Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 (same as bm25_filter.py)"""
        import re
        # Simple tokenization - lowercase and split
        tokens = re.findall(r'\b[a-z]+\b', text.lower())
        # Remove common words and short tokens
        COMMON_WORDS = {
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'will', 'can', 
            'are', 'was', 'were', 'been', 'have', 'has', 'had', 'does', 'did',
            'not', 'but', 'what', 'when', 'where', 'which', 'who', 'how', 'why',
            'all', 'would', 'there', 'their', 'your', 'more', 'other', 'some',
            'into', 'only', 'also', 'than', 'many', 'must', 'should', 'could'
        }
        return [t for t in tokens if t not in COMMON_WORDS and len(t) > 2]

    async def _load_corpus_for_bm25(self) -> None:
        """Load existing tool texts from Pinecone to fit BM25"""
        try:
            # Get all tools to build corpus
            results = self.index.query(
                vector=[0] * self.dimension,  # Dummy vector
                top_k=10000,  # Get all
                include_metadata=True
            )
            
            if results.matches:
                # Extract tool texts for BM25 corpus
                for match in results.matches:
                    metadata = match.metadata or {}
                    tool_text = metadata.get("tool_text", "")
                    if tool_text:
                        self.tool_corpus.append(tool_text)
                        self.corpus_tokens.append(self._tokenize(tool_text))
                
                # Index BM25 with existing corpus
                if self.corpus_tokens:
                    self.bm25.index(self.corpus_tokens)
                    self._bm25_fitted = True
                    logger.debug(f"Loaded {len(self.tool_corpus)} tools into BM25 corpus")
        except Exception as e:
            logger.warning(f"Failed to load corpus for BM25: {e}")
    
    def generate_tool_id(name: str, server_name: str, server_url: str) -> str:
        """Generate unique ID for a tool"""
        # Use SHA256 of tool name + server info for consistent IDs
        unique_string = f"{name}_{server_name}_{server_url}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]
    
    async def tool_exists(self, tool_id: str) -> bool:
        """Check if a tool already exists in the index"""
        try:
            result = self.index.fetch(ids=[tool_id])
            return tool_id in result.vectors
        except Exception:
            return False
    
    async def upsert_tool(
        self,
        tool_data: Dict[str, Any],
        embedding: List[float],
        server_name: str,
        server_url: str
    ) -> None:
        """
        Upsert a tool to Pinecone with hybrid search support
        
        Args:
            tool_data: Tool information
            embedding: Dense embedding vector
            server_name: MCP server name
            server_url: MCP server URL
        """
        try:
            tool_name = tool_data.get("name", "")
            tool_id = PineconeVectorStore.generate_tool_id(tool_name, server_name, server_url)
            
            # Create tool text for BM25
            tool_text = f"{tool_name} {tool_data.get('description', '')} {tool_data.get('category', '')}"
            
            # Add to corpus and reindex BM25 periodically
            self.tool_corpus.append(tool_text)
            tokens = self._tokenize(tool_text)
            self.corpus_tokens.append(tokens)
            
            # Reindex BM25 every 10 tools or if not fitted yet
            if len(self.tool_corpus) % 10 == 0 or not self._bm25_fitted:
                self.bm25.index(self.corpus_tokens)
                self._bm25_fitted = True
            
            # Note: bm25s doesn't generate sparse vectors like pinecone-text
            # We'll skip sparse vector for now and use dense embedding only
            sparse_vector = None
            
            # Prepare metadata
            metadata = {
                "name": tool_name,
                "description": tool_data.get("description", ""),
                "category": tool_data.get("category", ""),
                "server_name": server_name,
                "server_url": server_url,
                "tool_text": tool_text,  # Store for BM25 corpus rebuilding
                "parameter_count": len(tool_data.get("inputSchema", {}).get("properties", {}))
            }
            
            # Upsert to Pinecone with dense vector (sparse vector support removed for now)
            vector_data = {
                "id": tool_id,
                "values": embedding,
                "metadata": metadata
            }
            
            # Only add sparse_values if we have it
            if sparse_vector is not None:
                vector_data["sparse_values"] = sparse_vector
            
            self.index.upsert(vectors=[vector_data])
            
        except Exception as e:
            logger.error(f"Failed to upsert tool {tool_data.get('name', 'unknown')}: {e}")
            raise
    
    async def search_tools(
        self,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None,
        available_tool_names: Optional[List[str]] = None,
        alpha: float = 0.7
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for tools using hybrid search (dense + sparse)
        
        Args:
            query_embedding: Dense query embedding
            query_text: Original query text for BM25
            top_k: Number of results
            filter_metadata: Metadata filters
            available_tool_names: Filter by currently available tools
            alpha: Weight for dense vs sparse (0.7 = 70% dense, 30% sparse)
            
        Returns:
            List of (tool_metadata, score) tuples
        """
        try:
            # Build query parameters
            query_params = {
                "vector": query_embedding,
                "top_k": top_k,
                "include_metadata": True
            }
            
            # Add metadata filter if provided
            if filter_metadata:
                query_params["filter"] = filter_metadata
            
            # For now, skip sparse vector search since we're using bm25s differently
            # In the future, we could implement hybrid search by:
            # 1. Getting BM25 scores separately using self.bm25.retrieve()
            # 2. Combining with dense vector search results
            # 3. Re-ranking based on combined scores
            if self.bm25 and self._bm25_fitted:
                try:
                    # Could implement BM25 scoring here and combine with dense search
                    # For now, just use dense search
                    pass
                except Exception as e:
                    logger.warning(f"BM25 search failed: {e}")
            
            # Execute search
            results = self.index.query(**query_params)
            
            # Process results
            tools = []
            for match in results.matches:
                if not match.metadata:
                    continue
                
                tool_name = match.metadata.get("name", "")
                
                # Filter by available tools if specified
                if available_tool_names and tool_name not in available_tool_names:
                    continue
                
                tools.append((match.metadata, match.score))
            
            return tools
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_all_tools(
        self,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all tools, optionally filtered by category"""
        try:
            # Build filter
            filter_dict = {}
            if category:
                filter_dict["category"] = category
            
            # Query with dummy vector to get all results
            results = self.index.query(
                vector=[0] * self.dimension,
                top_k=10000,
                filter=filter_dict if filter_dict else None,
                include_metadata=True
            )
            
            return [match.metadata for match in results.matches if match.metadata]
            
        except Exception as e:
            logger.error(f"Failed to get all tools: {e}")
            raise


# ============= Vector Store Manager =============

class VectorStoreManager:
    """Manager for vector storage and tool search"""
    
    def __init__(
        self,
        use_cloud: bool = True,
        sync_tools: bool = True,
        pinecone_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        index_name: str = "mcp-tools-hybrid",
        embedding_model: str = "text-embedding-3-large"
    ):
        """
        Initialize vector store manager
        
        Args:
            use_cloud: Whether to use cloud storage (Pinecone)
            sync_tools: Whether to sync new tools to cloud
            pinecone_api_key: Pinecone API key
            openai_api_key: OpenAI API key for embeddings
            index_name: Pinecone index name
            embedding_model: OpenAI embedding model
        """
        self.use_cloud = use_cloud
        self.sync_tools = sync_tools
        self.initialized = False
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            api_key=openai_api_key,
            model=embedding_model
        )
        
        # Initialize vector store
        if use_cloud:
            self.vector_store = PineconeVectorStore(
                api_key=pinecone_api_key,
                index_name=index_name
            )
        else:
            # For now, cloud-only implementation
            raise NotImplementedError("Local vector store not implemented. Use cloud=True.")
    
    async def initialize(self) -> None:
        """Initialize the vector store"""
        if not self.initialized:
            await self.vector_store.initialize()
            self.initialized = True
            logger.debug("Vector store manager initialized")
    
    async def sync_tools_to_cloud(
        self,
        tools: List[Dict[str, Any]],
        server_name: str,
        server_url: str
    ) -> Dict[str, Any]:
        """
        Sync tools to cloud storage
        
        Args:
            tools: List of tools to sync
            server_name: MCP server name
            server_url: MCP server URL
            
        Returns:
            Sync statistics
        """
        if not self.use_cloud or not self.sync_tools:
            return {"synced": 0, "skipped": 0, "errors": 0}
        
        await self.initialize()
        
        synced = 0
        skipped = 0
        errors = 0
        
        for tool in tools:
            try:
                # Generate tool ID
                tool_id = PineconeVectorStore.generate_tool_id(
                    tool.get("name", ""),
                    server_name,
                    server_url
                )
                
                # Check if tool already exists
                if await self.vector_store.tool_exists(tool_id):
                    logger.debug(f"Tool {tool.get('name')} already exists, skipping")
                    skipped += 1
                    continue
                
                # Generate embedding
                embedding = await self.embeddings.embed_tool(tool)
                
                # Upsert to vector store
                await self.vector_store.upsert_tool(
                    tool_data=tool,
                    embedding=embedding,
                    server_name=server_name,
                    server_url=server_url
                )
                
                synced += 1
                logger.debug(f"Synced tool {tool.get('name')} to cloud")
                
            except Exception as e:
                logger.error(f"Error syncing tool {tool.get('name', 'unknown')}: {e}")
                errors += 1
        
        stats = {
            "synced": synced,
            "skipped": skipped,
            "errors": errors,
            "total": len(tools)
        }
        
        logger.debug(f"Tool sync completed: {stats}")
        return stats
    
    async def search_tools(
        self,
        query: str,
        top_k: int = 20,
        available_tool_names: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for tools using vector similarity
        
        Args:
            query: Search query
            top_k: Number of results
            available_tool_names: Filter by currently available tools
            filter_metadata: Additional metadata filters
            
        Returns:
            List of (tool_data, similarity_score) tuples
        """
        if not self.use_cloud:
            return []
        
        await self.initialize()
        
        # Generate query embedding
        query_embedding = await self.embeddings.embed_text(query)
        
        # Search in vector store
        results = await self.vector_store.search_tools(
            query_embedding=query_embedding,
            query_text=query,  # Pass original text for hybrid search
            top_k=top_k,
            filter_metadata=filter_metadata,
            available_tool_names=available_tool_names,
            alpha=0.7  # Favor semantic search slightly over keyword
        )
        
        # Log all scores for debugging
        if results:
            logger.debug(f"Vector search scores: {[(t[0]['name'], f'{t[1]:.3f}') for t in results[:5]]}")
        
        # Filter by minimum similarity score (cosine similarity threshold)
        min_similarity = 0.4  # Lowered threshold
        filtered_results = [(tool, score) for tool, score in results if score >= min_similarity]
        
        # Ensure we always return at least 3 tools
        if len(filtered_results) < 3 and len(results) >= 3:
            # Take top 3 regardless of score
            filtered_results = results[:3]
            logger.debug(f"Vector search: Returning top 3 tools despite low scores: {[(t[0]['name'], f'{t[1]:.3f}') for t in filtered_results]}")
        elif len(filtered_results) < 3:
            # Return all available results if less than 3 total
            filtered_results = results
        
        # Log search quality
        if filtered_results and filtered_results[0][1] >= min_similarity:
            logger.debug(f"Vector search: {len(filtered_results)} tools above {min_similarity} threshold (top score: {filtered_results[0][1]:.3f})")
        else:
            logger.debug(f"Vector search: Using top {len(filtered_results)} tools with scores: {[f'{t[1]:.3f}' for t in filtered_results]}")
        
        return filtered_results
    
    async def get_all_cloud_tools(
        self,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tools from cloud storage
        
        Args:
            category: Optional filter by category
            
        Returns:
            List of tools
        """
        if not self.use_cloud:
            return []
        
        await self.initialize()
        
        return await self.vector_store.get_all_tools(
            category=category
        )