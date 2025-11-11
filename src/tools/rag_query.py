from typing import Dict, Any
from .base import BaseTool
from ..memory import VectorDB
from src.llm.prompts import format_rag_context
from ..utils  import get_logger , config

logger = get_logger(__name__)


class RAGQueryTool(BaseTool):
    """
    Query the vector database for relevant documents.
    
    This tool searches:
    - PDFs , Text files uploaded via ingest_documents.py

    """
    
    def __init__(self, vector_db: VectorDB = None, top_k: int = None):
        """
        Initialize RAG query tool.
        
        Args:
            vector_db: VectorDB instance (if None, creates new one)
            top_k: Default number of chunks to retrieve
        
        """
        self.vector_db = vector_db or VectorDB()
        self.top_k = top_k or config.RAG_TOP_K
        
        doc_count = self.vector_db.get_document_count()
        logger.info(f"RAGQueryTool initialized: {doc_count} documents in database")
    
    @property
    def name(self) -> str:
        return "rag_query"
    
    @property
    def description(self) -> str:
        return """Search the user's uploaded or saved documents. 
    Use when :
    - user asks about previously uploaded files (PDFs, texts) or certain pdf document
    - user asks to search in local files or database

    Do NOT use for general knowledge, current events, or web data."""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query. Be specific. Example: 'project deadline and milestones' not just 'project'"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of relevant chunks to retrieve",
                    "default": self.top_k,
                    "minimum": 1,
                    "maximum": 10
                },
                "filter_source": {
                    "type": "string",
                    "description": "Optional: filter by source filename (e.g., 'meeting_notes.pdf')"
                }
            },
            "required": ["query"]
        }
    
    def execute(
        self,
        query: str,
        top_k: int = None,
        filter_source: str = None
    ) -> str:
        """
        Execute RAG query.
        
        Args:
            query: Search query (natural language)
            top_k: Number of chunks to retrieve (overrides default)
            filter_source: Optional source filter
        
        Returns:
            Formatted search results as string
        
        """
        if not query.strip():
            return "Error: Search query cannot be empty"
        
        # Use provided top_k or default
        top_k = top_k or self.top_k
        
        # Clamp to valid range
        top_k = max(1, min(10, top_k))
        
        logger.info(f"RAG query: '{query}' (top_k={top_k}, filter={filter_source})")
        
        # Check if database has documents
        doc_count = self.vector_db.get_document_count()
        
        if doc_count == 0:
            logger.warning("Vector database is empty")
            return """No documents found in the database. 

The user hasn't uploaded any documents yet. They can:
- Upload PDFs/text files using: python scripts/ingest_documents.py --file document.pdf

Let the user know their document database is empty."""
        
        try:
            # Build metadata filter if source specified
            filter_metadata = None
            if filter_source:
                filter_metadata = {"source": filter_source}
            
            # Query vector database
            results = self.vector_db.query(
                query_text=query,
                top_k=top_k,
                filter_metadata=filter_metadata
            )
            
            if not results:
                logger.warning(f"No results found for query: {query}")
                return self._format_no_results(query, filter_source)
            
            # Format results for LLM
            formatted = format_rag_context(results)
            
            logger.info(f"RAG query completed: {len(results)} results returned")
            return formatted
        
        except Exception as e:
            error_msg = f"RAG query failed: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def _format_no_results(self, query: str, filter_source: str = None) -> str:
        """
        Format message when no results found.
        
        Args:
            query: Original query
            filter_source: Source filter if used
        
        Returns:
            Formatted no-results message
        
        """
        # Get available sources
        sources = self.vector_db.list_sources()
        
        message = f"No relevant documents found for '{query}'."
        
        if filter_source:
            message += f"\n\nSearched in: {filter_source}"
            
            if filter_source not in sources:
                message += f"\nNote: Source '{filter_source}' not found in database."
        
        if sources:
            message += f"\n\nAvailable sources in database: {', '.join(sources[:5])}"
            if len(sources) > 5:
                message += f" (and {len(sources) - 5} more)"
        
        message += "\n\nSuggestions:"
        message += "\n- Try different search terms"
        message += "\n- Check if the information was actually uploaded"
        message += "\n- Ask user to clarify what they're looking for"
        
        return message
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.
        
        Returns:
            Dictionary with stats:
            - document_count: Total chunks in DB
            - sources: List of source files
            - source_count: Number of unique sources
        
        Why this method?
        - Debugging: Check what's in the database
        - User info: Show what documents are available
        - Health check: Verify database is working
        """
        doc_count = self.vector_db.get_document_count()
        sources = self.vector_db.list_sources()
        
        return {
            "document_count": doc_count,
            "sources": sources,
            "source_count": len(sources)
        }

