from typing import List
from .base import BaseTool
from ..utils import get_logger, config

logging = get_logger(__name__)


class ToolSelector:
    """
    Intelligently selects which tools to include based on conversation context.
    """
    
    def __init__(self, all_tools: List[BaseTool]):
        """
        Initialize tool selector.
        
        Args:
            all_tools: List of all available tools
        """
        self.all_tools = {tool.name: tool for tool in all_tools}
        
        # Tools that are always included 
        self.always_include = ["save_read_information", "file_writer"]
        
        # Keyword mapping for conditional tools
        self.keyword_map = {
            "web_search": [
                "search", "google", "find", "look up", "latest", "recent",
                "news", "weather", "current", "today", "now", "what's"
            ],
            "rag_query": [
                "document", "uploaded", "pdf", "file", "my notes",
                "what did i upload", "search my", "in my documents"
            ],
            "gmail_draft": [
                "email", "gmail", "draft", "send", "compose",
                "write email", "message to"
            ] 
        }
        
        logging.info(f"ToolSelector initialized with {len(self.all_tools)} tools")
        if not config.INCLUDE_GMAIL_DRAFT:
            del self.keyword_map['gmail_draft']

        if not config.INCLUDE_SEARCH_SERPAPI:
            del self.keyword_map['web_search']
    
    def select_tools(
        self,
        recent_messages: List[dict],
        include_all: bool = False
    ) -> List[BaseTool]:
        """
        Select relevant tools based on recent conversation context.
        
        Args:
            recent_messages: Recent messages (last 3-5 messages)
            include_all : If True, include all tools when no keywords match
        
        Returns:
            List of relevant tools
        """
        # Always include these tools
        selected_tool_names = set(self.always_include)
        
        # Extract recent text (last 4 messages)
        recent_text = self._extract_text_from_messages(recent_messages[-4:]).lower()

        # Check each conditional tool
        for tool_name, keywords in self.keyword_map.items():
            if any(keyword in recent_text for keyword in keywords):
                selected_tool_names.add(tool_name)
                logging.debug(f"Including tool: {tool_name} (keyword match)")
        
        # If no conditional tools matched, use fallback
        if len(selected_tool_names) == len(self.always_include):
            if include_all:
                logging.debug("No keyword matches, including all tools (fallback)")
                selected_tool_names = set(self.all_tools.keys())
            else:
                logging.debug("No keyword matches, using only base tools")
        
        # Get tool objects
        selected_tools = [
            self.all_tools[name]
            for name in selected_tool_names
            if name in self.all_tools
        ]
        
        logging.info(f"Selected {len(selected_tools)} tools: {[t.name for t in selected_tools]}")
        
        return selected_tools
    
    def _extract_text_from_messages(self, messages: List[dict]) -> str:
        """
        Extract text content from messages.
        
        Args:
            messages: List of message dicts
        
        Returns:
            Combined text
        """
        text_parts = []
        
        for msg in messages:
            # Only look at user and assistant messages
            if msg.get("role") in ["user", "assistant"]:
                content = msg.get("content", "")
                if content:
                    text_parts.append(content)
        
        return " ".join(text_parts)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all available tools .
 
        """
        return list(self.all_tools.values())
    
    def add_tool(self, tool: BaseTool):
        """
        Add a new tool to the selector.
        """
        self.all_tools[tool.name] = tool
        logging.info(f"Added tool: {tool.name}")
    
    def remove_tool(self, tool_name: str):
        """
        Remove a tool from the selector.
        """
        if tool_name in self.all_tools:
            del self.all_tools[tool_name]
            logging.info(f"Removed tool: {tool_name}")


