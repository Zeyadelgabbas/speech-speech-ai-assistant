from typing import List, Dict, Optional
from datetime import datetime
from ..utils import get_logger , config , count_tokens

logger = get_logger(__name__)


class SessionMemory:
    """
    Manages the current conversation session in memory.
    
    This stores:
    - All messages in current conversation (user + assistant + tool results)
    - Timestamp of session start
    - Message count
    
    """
    
    def __init__(self, max_messages: Optional[int] = None):
        """
        Initialize session memory.
        
        Args:
            max_messages: Maximum number of messages to keep in memory
                If None, uses config.SESSION_MEMORY_MAX_TOKENS to calculate
                None = unlimited (will truncate based on token count instead)
        

        Two strategies:
        1. Message-based truncation: Keep last N messages
        2. Token-based truncation: Keep messages within token budget
        
        We use token-based (more precise cost control).
        """
        self.messages: List[Dict[str, any]] = []
        self.max_messages = max_messages
        self.session_start = datetime.now().strftime("%Y-%m-%d,%H:%M:%S")
        self.session_id = None  # Will be set when saved to database
        
        logger.info(f"SessionMemory initialized: max_messages={max_messages}")
    
    def add_message(self, role: str, content: str, tool_calls: Optional[List] = None) ->None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Message role ("user", "assistant", "system", "tool")
            content: Message content (text)
            tool_calls: Optional tool calls (for assistant messages with function calling)
        
        Message roles:
        - "user": What the user said
        - "assistant": What the LLM responded
        - "system": Instructions/context (usually only at start)
        - "tool": Tool execution results
        
        Why this method exists:
        After every user input and assistant response, we add to memory
        so the LLM has context for future messages.
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add tool_calls if present (for assistant messages)
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        self.messages.append(message)
        
        logger.info(f"Added message: role={role}, length={len(content) if content else 0}")
        
        # Check if we need to truncate (optional, based on max_messages)
        if self.max_messages and len(self.messages) > self.max_messages:
            self._truncate_old_messages()
    
    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        """
        Add a tool execution result to conversation history.
        
        Args:
            tool_call_id: ID of the tool call (from LLM response)
            tool_name: Name of the tool that was executed
            result: Tool execution result (as string)
        
        Why this method exists:
        After executing a tool (web_search, rag_query, etc.), we need to
        add the result back to the conversation so the LLM can use it.
        
        This is a specialized version of add_message() for tool results.
        """
        message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        logger.info(f"Added tool result: tool={tool_name}, length={len(result)}")
    
    def get_messages(self, include_system: bool = False) -> List[Dict[str, any]]:
        """
        Get all messages in the current session.
        
        Args:
            include_system: Whether to include system messages
                Usually False (system prompt is added separately each time)
        
        Returns:
            List of message dictionaries
        
        Why this method exists:
        When calling the LLM, we need to pass the full conversation history.
        This method returns it in the format OpenAI expects.
        
        Usage:
            messages = [
                {"role": "system", "content": system_prompt},
                *session_memory.get_messages(),
                {"role": "user", "content": new_user_input}
            ]
        """
        if include_system:
            return self.messages.copy()
        
        # Filter out system messages (they're added fresh each time)
        return [msg for msg in self.messages if msg["role"] != "system"]
    
    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """
        Get messages formatted for OpenAI API (clean format, no timestamps).
        
        Returns:
            List of messages with only required fields (role, content, tool_calls)
        
        Why this method exists:
        Our internal messages have extra fields (timestamp, m etadata).
        OpenAI API only needs role, content, and tool_calls.
        This method strips extra fields.
        """
        clean_messages = []
        
        for msg in self.messages:
            clean_msg = {"role": msg["role"]}
            
            # Add content if present
            if "content" in msg and msg["content"] is not None:
                clean_msg["content"] = msg["content"]
            
            # Add tool_calls if present (assistant messages)
            if "tool_calls" in msg:
                clean_msg["tool_calls"] = msg["tool_calls"]
            
            # Add tool_call_id if present (tool messages)
            if "tool_call_id" in msg:
                clean_msg["tool_call_id"] = msg["tool_call_id"]
            
            # Add name if present (tool messages)
            if "name" in msg:
                clean_msg["name"] = msg["name"]
            
            clean_messages.append(clean_msg)
        
        return clean_messages
    
    def _truncate_old_messages(self) -> None:
        """
        Remove old messages to stay within max_messages limit.
        
        Strategy:
        - Keep first message if it's system (instructions)
        - Remove oldest user/assistant messages
        - Always keep recent messages
        
        Why this method exists:
        Long conversations can exceed context limits or become expensive.
        We keep recent messages (most relevant) and drop old ones.
        """
        if not self.max_messages:
            return
        
        # Check if first message is system
        has_system = self.messages and self.messages[0]["role"] == "system"
        
        if has_system:
            # Keep system + last (max_messages - 1) messages
            self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]
        else:
            # Keep last max_messages
            self.messages = self.messages[-self.max_messages:]
        
        logger.info(f"Truncated to {len(self.messages)} messages")
    
    def truncate_by_tokens(self, max_tokens: int,count_tokens :callable = count_tokens):
        """
        Truncate messages to fit within token budget.
        
        Args:
            max_tokens: Maximum total tokens to keep
            count_tokens_func: Function to count tokens in text
                Signature: count_tokens_func(text: str) -> int
        
        Why this method exists:
        Token-based truncation is more precise than message-based.
        We want to maximize context while staying under API limits.
        
        Strategy:
        1. Count tokens in all messages
        2. If over budget, remove oldest messages (keep system + recent)
        3. Continue until under budget
        """
        # Count total tokens
        total_tokens = 0
        for msg in self.messages:
            content = msg.get("content", "")
            if content:
                total_tokens += count_tokens(content)
        
        # If under budget, no truncation needed
        if total_tokens <= max_tokens:
            logger.info(f"Session memory: {total_tokens} tokens (under budget)")
            return
        
        logger.info(f"Session memory: {total_tokens} tokens (over {max_tokens} budget), truncating...")
        
        # Keep system message if present
        has_system = self.messages and self.messages[0]["role"] == "system"
        system_msg = [self.messages[0]] if has_system else []
        other_messages = self.messages[1:] if has_system else self.messages
        
        # Remove oldest messages until under budget
        while total_tokens > max_tokens and len(other_messages) > 1:
            # Remove oldest message
            removed = other_messages.pop(0)
            removed_tokens = count_tokens(removed.get("content", ""))
            total_tokens -= removed_tokens
            logger.debug(f"Removed message ({removed_tokens} tokens)")
        
        # Reconstruct messages list
        self.messages = system_msg + other_messages
        logger.info(f"Truncated to {len(self.messages)} messages ({total_tokens} tokens)")
    
    def get_last_n_messages(self, n: int) -> List[Dict[str, any]]:
        """
        Get the last N messages.
        """
        return self.messages[-n:] if n < len(self.messages) else self.messages.copy()
    
    def get_message_count(self) -> int:
        """
        Get the total number of messages in current session.
        
        Returns:
            Message count
        """
        return len(self.messages)
    
    def get_session_duration(self) -> str:
        """
        Get how long the current session has been active.
        
        Returns:
            Human-readable duration string (e.g., "15 minutes")
        
        Why this method exists:
        For UI/logging, show how long user has been in this session.
        """
        duration = datetime.now() - self.session_start
        
        seconds = int(duration.total_seconds())
        
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    
    def clear(self):
        """
        Clear all messages (start fresh session).
        
        Why this method exists:
        - User wants to start new topic without previous context
        - Session was saved, starting new one
        - Error recovery (clear corrupted state)
        """
        message_count = len(self.messages)
        self.messages = []
        self.session_start = datetime.now()
        self.session_id = None
        
        logger.info(f"Session memory cleared ({message_count} messages removed)")
    
    def to_dict(self) -> Dict[str, any]:
        """
        Export session to dictionary (for saving to database).
        
        Returns:
            Dictionary with session data
        
        Why this method exists:
        When user says "save session", we export to dict and store in SQLite.
        """
        return {
            "messages": self.messages,
            "session_start": self.session_start.isoformat(),
            "message_count": len(self.messages),
            "duration": self.get_session_duration()
        }
    
    def from_dict(self, data: Dict[str, any]):
        """
        Load session from dictionary (when resuming saved session).
        
        Args:
            data: Dictionary with session data (from database)
        
        Why this method exists:
        When user resumes a saved session, we restore the conversation state.
        """
        self.messages = data.get("messages", [])
        self.session_start = datetime.fromisoformat(data.get("session_start", datetime.now().isoformat()))
        self.session_id = data.get("session_id")
        
        logger.info(f"Loaded session: {len(self.messages)} messages")
    
    def get_conversation_summary(self) -> str:
        """
        Generate a brief text summary of the conversation.
        
        Returns:
            Summary string
        
        Why this method exists:
        For displaying session list ("Project planning - 15 messages")
        or generating quick previews.
        """
        if not self.messages:
            return "Empty session"
        
        # Get first user message as topic indicator
        first_user_msg = next((msg for msg in self.messages if msg["role"] == "user"), None)
        
        if first_user_msg:
            topic = first_user_msg.get("content", "")[:50]
            if len(first_user_msg.get("content", "")) > 50:
                topic += "..."
        else:
            topic = "Conversation"
        
        return f"{topic} - {len(self.messages)} messages"


