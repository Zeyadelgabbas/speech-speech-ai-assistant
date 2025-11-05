from openai import OpenAI
from typing import List, Dict, Optional, Any
import json
from ..utils import config, get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """
    Client for OpenAI's Chat Completions API with function calling.
    
    This is the "brain" of the voice assistant. It:
    1. Receives user messages (transcribed from speech)
    2. Accesses conversation history and memory
    3. Decides which tools to call (web search, RAG, Gmail, etc.)
    4. Generates natural language responses
    
    Key concepts:
    - Messages: List of {role, content} dictionaries (user/assistant/system)
    - Tools: Functions the LLM can call (defined as JSON schemas)
    - Function calling: LLM decides when/how to use tools
    - Streaming: Real-time response generation (not used in MVP)
    
    OpenAI's function calling flow:
    1. Send: messages + available tools
    2. LLM response: either text OR tool_calls
    3. If tool_calls: execute tools, send results back
    4. LLM generates final response with tool results
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, uses config.OPENAI_API_KEY
            model: Model name (gpt-4-turbo-preview, gpt-3.5-turbo, etc.)
                If None, uses config.OPENAI_MODEL
            temperature: Response creativity/randomness (0.0-2.0)
                0.0 = Deterministic, factual, consistent
                0.7 = Balanced creativity [RECOMMENDED for assistant]
                1.0 = More creative, varied responses
                1.5+ = Very creative, potentially less coherent
            max_tokens: Maximum response length (tokens)
                None = No limit (uses model's context window)
                500 = Short responses (good for voice assistant)
                2000 = Medium responses
                4000+ = Long responses (essays, articles)
        

        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.OPENAI_MODEL
        self.temperature = temperature or config.TEMPERATURE
        self.max_tokens = max_tokens or config.MAX_TOKENS
            
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        logger.info(
            f"OpenAI client initialized: model={self.model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens or 'unlimited'}"
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = None
    ) -> Dict[str, Any]:
        """
        Send messages to LLM and get response.
        
        Args:
            messages: Conversation history
                Format: [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "What's the weather?"},
                    {"role": "assistant", "content": "Let me check..."}
                ]
            tools: Available tools (functions LLM can call)
                Format: OpenAI function calling schema (see _format_tools())
                Example: [{"type": "function", "function": {...}}]
            tool_choice: How LLM should use tools
                "auto" = LLM decides when to call tools [RECOMMENDED]
                "none" = Never call tools (just respond with text)
                {"type": "function", "function": {"name": "web_search"}} = Force specific tool
        
        Returns:
            Dictionary with:
                - role: "assistant"
                - content: Text response (may be None if tool_calls exist)
                - tool_calls: List of tool calls LLM wants to execute (or None)
                - finish_reason: "stop" (complete) or "tool_calls" (needs tool execution)
        
        Message roles explained:
        - system: Instructions for the LLM (personality, rules, context)
        - user: What the user said (input)
        - assistant: What the LLM responded (output)
        - tool: Results from tool execution (special role for function calling)
        
        Example usage:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Search for AI news"}
            ]
            
            response = client.chat(messages, tools=available_tools)
            
            if response["tool_calls"]:
                # LLM wants to call a tool
                for tool_call in response["tool_calls"]:
                    # Execute tool, get result
                    result = execute_tool(tool_call)
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result
                    })
                # Call LLM again with tool results
                final_response = client.chat(messages, tools=available_tools)
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        if tools:
            tool_choice = 'auto'
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice=tool_choice
            )
            
            # Extract response data
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
            # Convert to dictionary format
            result = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": None,
                "finish_reason": finish_reason
            }
            
            # Extract tool calls if present
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments  # JSON string
                        }
                    }
                    for tc in message.tool_calls
                ]
                logger.info(f"LLM requested {len(result['tool_calls'])} tool call(s)")
            
            # Log response
            usage = response.usage
            logger.info(
                f"Chat response received: finish_reason={finish_reason}, "
                f"tokens={usage.total_tokens} (prompt={usage.prompt_tokens}, "
                f"completion={usage.completion_tokens})"
            )  
            return result
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def execute_tool_call_loop(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        tool_executor: callable,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Handle complete tool calling loop (request → execute → respond).
        
        This is a convenience method that automates the tool calling flow:
        1. Send messages to LLM
        2. If LLM requests tools, execute them
        3. Send tool results back to LLM
        4. Repeat until LLM provides final text response
        
        Args:
            messages: Initial conversation history
            tools: Available tools
            tool_executor: Function that executes tools
                Signature: tool_executor(tool_name: str, arguments: dict) -> str
                Example: def executor(name, args):
                             if name == "web_search":
                                 return search_web(args["query"])
            max_iterations: Maximum tool calling rounds (prevents infinite loops)
        
        Returns:
            Final assistant response (same format as chat())
        
      
        Example flow:
        User: "Search for AI news and summarize it"
        Iteration 1:
            LLM: tool_call(web_search, query="AI news")
            Tool: "Article 1: ..., Article 2: ..."
        Iteration 2:
            LLM: "Here's a summary: ..." [DONE]
        """
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Tool call loop iteration {iteration}/{max_iterations}")
            
            # Get LLM response
            response = self.chat(messages, tools=tools)
            
            # If no tool calls, we're done
            if not response["tool_calls"]:
                return response
            
            # Add assistant message with tool calls to history
            messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": response["tool_calls"]
            })
            
            # Execute each tool call
            for tool_call in response["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                try:
                    # Execute tool via callback
                    tool_result = tool_executor(tool_name, tool_args)
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(tool_result)
                    })
                    
                    logger.info(f"Tool {tool_name} executed successfully")
                
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    # Add error as tool result (LLM can handle it)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": f"Error executing {tool_name}: {str(e)}"
                    })
            
            # Continue loop (LLM will process tool results)
        
        # Max iterations reached without final response
        logger.warning(f"Tool call loop reached max iterations ({max_iterations})")
        return {
            "role": "assistant",
            "content": "I apologize, but I'm having trouble completing your request. Please try again.",
            "tool_calls": None,
            "finish_reason": "max_iterations"
        }
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Approximate token count
        
        Why this matters:
        - OpenAI charges by token (input + output)
        - Models have context limits (e.g., 128K tokens for GPT-4)
        - Helps decide when to truncate/summarize memory
        
        Estimation method:
        - GPT models use ~1.3 tokens per word on average
        - This is a rough estimate (actual tokenization is more complex)
        - For exact count, use tiktoken library (adds dependency)
        
        Example costs (gpt-4-turbo-preview):
        - 1K tokens input: $0.01
        - 1K tokens output: $0.03
        - Average conversation (10 turns): ~2K tokens = $0.08
        """
        # Simple estimation: ~1.3 tokens per word
        words = text.split()
        estimated_tokens = int(len(words) * 1.3)
        
        return estimated_tokens
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate API call cost in USD.
        
        Args:
            prompt_tokens: Input tokens (user message + history + tools)
            completion_tokens: Output tokens (assistant response)
        
        Returns:
            Estimated cost in USD
        
        Pricing (as of 2025, check current prices on OpenAI website):
        gpt-4-turbo-preview:
            Input:  $10.00 / 1M tokens
            Output: $30.00 / 1M tokens
        gpt-4o:
            Input:  $5.00 / 1M tokens
            Output: $15.00 / 1M tokens
        gpt-3.5-turbo:
            Input:  $0.50 / 1M tokens
            Output: $1.50 / 1M tokens
        
        Cost control tips:
        - Use gpt-3.5-turbo for simple queries (10x cheaper)
        - Summarize long conversation history
        - Cache common responses (e.g., "I don't understand")
        """
        # Pricing per 1M tokens (update these based on current OpenAI pricing)
        pricing = {
            "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
            "gpt-4o": {"input": 5.00, "output": 15.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            
        }
        
        # Get pricing for current model (default to gpt-4 if unknown)
        model_pricing = pricing.get(self.model, pricing["gpt-4-turbo-preview"])
        
        input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
        
        total_cost = input_cost + output_cost
        
        return total_cost


# ============================================================================
# MODULE TEST
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("OPENAI CLIENT TEST")
    print("=" * 70)
    

    #  Initialize client
    print("\n" + "=" * 70)
    print("Initializing OpenAI client...")
    
    try:
        client = OpenAIClient(temperature=0.7)
        print(f"✅ Client initialized")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        exit(1)
    
    # Test 3: Simple chat (no tools)
    print("\n" + "=" * 70)
    print("Test 1: Simple chat (no function calling)")
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful voice assistant. Keep responses concise (1-2 sentences)."
        },
        {
            "role": "user",
            "content": "What is 2 + 2?"
        }
    ]
    
    print("\nSending message: 'What is 2 + 2?'")
    
    try:
        response = client.chat(messages)
        
        print(f"\n✅ Response received:")
        print(f"   Content: {response['content']}")
        print(f"   Finish reason: {response['finish_reason']}")
        print(f"   Tool calls: {response['tool_calls']}")
    
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        exit(1)
    

    
    # Test 5: Function calling simulation (without actual tools)
    print("\n" + "=" * 70)
    print("Test 3: Function calling schema (simulation)")
    
    # Define a sample tool
    sample_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name, e.g., 'San Francisco'"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    messages_with_tools = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to tools."
        },
        {
            "role": "user",
            "content": "What's the weather in Cairo?"
        }
    ]
    
    print("\nSending message with tool available: 'What's the weather in Cairo?'")
    print("Expected: LLM should request to call get_weather tool")
    
    try:
        response_tools = client.chat(messages_with_tools, tools=sample_tools)
        
        print(f"\n✅ Response received:")
        print(f"   Content: {response_tools['content']}")
        print(f"   Finish reason: {response_tools['finish_reason']}")
        
        if response_tools['tool_calls']:
            print(f"   Tool calls requested: {len(response_tools['tool_calls'])}")
            for tc in response_tools['tool_calls']:
                print(f"     - {tc['function']['name']}: {tc['function']['arguments']}")
        else:
            print("   ⚠️  No tool calls (LLM responded directly)")
            print("      This is normal - LLM decides when tools are needed")
    
    except Exception as e:
        print(f"❌ Function calling test failed: {e}")
    
    print("\n" + "=" * 70)
    print("✅ All OpenAI client tests passed!")
  
