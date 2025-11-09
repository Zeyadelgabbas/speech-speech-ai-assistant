import requests
from typing import Dict, Any
from .base import BaseTool
from ..utils import get_logger , config

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """
    Search the web using SerpAPI (Google Search API).
    
    Why SerpAPI?
    - Provides Google search results via API
    - No scraping needed (avoids legal issues)
    - Structured JSON results (easy to parse)
    - Free tier: 100 searches/month
    - Paid: $50/month for 5000 searches
    
    Alternative APIs:
    - Bing Search API: Microsoft's offering
    - Brave Search API: Privacy-focused
    - Google Custom Search: Limited free tier
    
    """
    
    def __init__(self, api_key: str = None, num_results: int = 3):
        """
        Initialize web search tool.
        
        Args:
            api_key: SerpAPI key (if None, uses config.SERP_API_KEY)
            num_results: Default number of results to return (1-10)
        """
        self.api_key = api_key or config.SERP_API_KEY
        self.num_results = num_results
        self.base_url = "https://serpapi.com/search"
        
        if not self.api_key or self.api_key == "your_serpapi_key_here":
            logger.warning("SerpAPI key not configured")
        
        logger.info("WebSearchTool initialized")
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        description = """Search Google. Use for: current events, real-time data (weather/stocks), recent info post-Jan 2025 . eg: listing schools in cairo
          NOT for: history, definitions, math."""
        return description
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query. Be concise (3-6 words). Example: 'weather Cairo Egypt' not 'Can you tell me what the weather is in Cairo, Egypt?'"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default: 3",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }
    
    def execute(self, query: str, num_results: int = None) -> str:
        """
        Execute web search.
        
        Args:
            query: Search query
            num_results: Number of results (overrides default if provided)
        
        Returns:
            Formatted search results as string
        
        """
        if not query.strip():
            return "Error: Search query cannot be empty"
        
        # Use provided num_results or default
        num_results = num_results or self.num_results
        
        # Clamp to valid range
        num_results = max(1, min(10, num_results))
        
        logger.info(f"Searching web: '{query}' (num_results={num_results})")
        
        # Check if API key is configured
        if not self.api_key or self.api_key == "your_serpapi_key_here":
            logger.error("SerpAPI key not configured")
            return self._get_demo_results(query)
        
        try:
            # Call SerpAPI
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "engine": "google"  # Use Google search
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract organic results
            organic_results = data.get("organic_results", [])
            
            if not organic_results:
                logger.warning(f"No results found for query: {query}")
                return f"No search results found for '{query}'. Try a different query."
            
            # Format results
            formatted = self._format_results(organic_results[:num_results], query)
            
            logger.info(f"Search completed: {len(organic_results)} results")
            return formatted
        
        except requests.exceptions.Timeout:
            error_msg = "Search request timed out. Please try again."
            logger.error(f"SerpAPI timeout: {query}")
            return error_msg
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Search failed: {str(e)}"
            logger.error(f"SerpAPI request error: {e}")
            return error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error during search: {str(e)}"
            logger.error(f"Search error: {e}")
            return error_msg
    
    def _format_results(self, results: list, query: str) -> str:
        """
        Format search results for LLM consumption.
        
        Args:
            results: List of search results from SerpAPI
            query: Original search query
        
        Returns:
            Formatted string
        
        """
        formatted = f"Search results for '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No description available")
            link = result.get("link", "")
            
            formatted += f"{i}. {title}\n"
            formatted += f"   {snippet}\n"
            
            if link:
                formatted += f"   Source: {link}\n"
            
            formatted += "\n"
        
        # Add instruction for LLM
        formatted += "Synthesize this information into a natural, concise response. Do not quote sources directly unless specifically asked."
        
        return formatted
    
    def _get_demo_results(self, query: str) -> str:
        """
        Return demo results when API key not configured.
        
        Args:
            query: Search query
        
        Returns:
            Mock search results
        
        Why demo mode?
        - Allows testing without API key
        - Shows expected result format
        - Users can try the system before getting API keys
        """
        logger.info("Returning demo results (API key not configured)")
        
        return f"""Search results for '{query}' (DEMO MODE - API key not configured):

1. Example Result 1
   This is a sample search result. To get real search results, configure SERP_API_KEY in .env file.
   Source: https://example.com

2. Example Result 2
   Another sample result. Sign up at https://serpapi.com/ to get your API key.
   Source: https://example.com

Note: These are placeholder results. Configure SerpAPI key to enable real web search."""
