from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..utils import get_logger , config

logging = get_logger(__name__)


class BaseTool(ABC):
    """
    Abstract base class for all tools.
     
    Every tool must implement:
    - name: Unique tool identifier
    - description: What the tool does 
    - parameters_schema: JSON schema for arguments
    - execute(): The actual tool logic
    
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique tool name (used by LLM to call it).
        
        Example: "web_search", "rag_query", "gmail_draft"
        
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Description of what the tool does.
        
        Note : This is what the LLM reads to decide when to use the tool!

        """
        pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """
        JSON Schema defining the tool's parameters.
        
        Format follows OpenAI's function calling schema:
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return"
                }
            },
            "required": ["query"]
        }
        
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific arguments (defined in parameters_schema)
        
        Returns:
            Tool result as string (will be sent back to LLM)
        
        """
        pass
    
    def get_openai_tool_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.
        
        Returns:
            Dictionary in OpenAI's expected format:
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate that provided parameters match the schema.
        
        Args:
            **kwargs: Parameters to validate
        
        Returns:
            True if valid, False otherwise
        """
        required = self.parameters_schema.get("required", [])
        properties = self.parameters_schema.get("properties", {})
        
        # Check required parameters
        for param in required:
            if param not in kwargs:
                logging.error(f"Missing required parameter: {param}")
                return False
        
        # Check parameter types (basic)
        for param, value in kwargs.items():
            if param not in properties:
                logging.warning(f"Unexpected parameter: {param}")
                continue
            
            expected_type = properties[param].get("type")
            
            if expected_type == "string" and not isinstance(value, str):
                logging.error(f"Parameter {param} should be string, got {type(value)}")
                return False
            
            if expected_type == "integer" and not isinstance(value, int):
                logging.error(f"Parameter {param} should be integer, got {type(value)}")
                return False
        
        return True
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<{self.__class__.__name__}: {self.name}>"


class ToolRegistry:
    """
    Registry to manage all available tools.
    """
    
    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        logging.info("ToolRegistry initialized")
    
    def register(self, tool: BaseTool):
        """
        Register a tool.
        
        Args:
            tool: Tool instance (must inherit from BaseTool)
        
        Raises:
            ValueError: If tool name already registered
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")
        
        if tool.name in self._tools:
            logging.error()
            raise ValueError(f"Tool '{tool.name}' already registered")
        
        self._tools[tool.name] = tool
        logging.info(f"Registered tool: {tool.name}")
    
    def unregister(self, tool_name: str):
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to remove
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logging.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Tool name
        
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools
    
    def list_tools(self) -> list:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_all_schemas(self) -> list:
        """
        Get OpenAI schemas for all registered tools.
        
        Returns:
            List of tool schemas in OpenAI format
        
        Usage:
            schemas = registry.get_all_schemas()
            response = llm_client.chat(messages, tools=schemas)
        """
        return [tool.get_openai_tool_schema() for tool in self._tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Tool result as string
        
        Raises:
            ValueError: If tool not found
        
        This is the main entry point for tool execution.
        Called by the LLM client after receiving tool_calls from GPT.
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            error_msg = f"Tool '{tool_name}' not found"
            logging.error(error_msg)
            return f"Error: {error_msg}"
        
        # Validate parameters
        if not tool.validate_parameters(**kwargs):
            error_msg = f"Invalid parameters for tool '{tool_name}'"
            logging.error(error_msg)
            return f"Error: {error_msg}"
        
        # Execute tool
        logging.info(f"Executing tool: {tool_name} with args: {kwargs}")
        
        try:
            result = tool.execute(**kwargs)
            logging.info(f"Tool {tool_name} executed successfully")
            return result
        
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logging.error(f"{error_msg} (tool={tool_name})")
            return f"Error: {error_msg}"
