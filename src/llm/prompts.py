from typing import Dict, Optional
from datetime import datetime
from ..utils import config , get_logger

logging = get_logger(__name__)


def get_system_prompt(
    user_summary: Optional[str] = None,
    include_tools: bool = True
) -> str:
    """
    Generate the main system prompt for the voice assistant.
    
    Args:
        user_summary: User profile/preferences loaded from user_summary.txt
        include_tools: Whether to include tool usage instructions
    Returns:
        Complete system prompt string
    
    """
    # Current date/time for context
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    current_time = datetime.now().strftime("%I:%M %p")
    
    # Base personality and role
    prompt = """You are a helpful, friendly voice assistant. Today is {current_date} and time is {current_time}.

## Your Personality
- Be conversational and natural (this is a voice conversation, not text chat)
- Keep responses concise (short responses if query is simple)
- Be proactive: offer relevant suggestions when appropriate
- Use a warm, professional tone

Note : Dont apply markdowns like '*'
""".format(current_date=current_date,current_time=current_time)
    
    # Add user context if available
    if user_summary:
        prompt += f"""
## User Profile
{user_summary}

Use this context to personalize responses, but don't reference it explicitly unless relevant.
"""
    
    # Add tool usage instructions
    if include_tools:
        prompt__ = """
## Available Tools
You have access to several tools. Use them proactively when needed:

**web_search**: For current events, news, recent information, facts you don't know

**rag_query**: Search user's uploaded documents and saved information

**gmail_draft**: Create email drafts (does NOT send, only creates draft)

**file_writter**: saves and exports (summaries , chats , search results , etc) to file

 Note: If a tool fails, acknowledge it gracefully and offer alternatives
"""
    return prompt.strip()


def get_tool_usage_prompt(tool_name: str) -> str:
    """
    Get specific instructions for using a particular tool.
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Instructions for that tool
    
    Why this exists:
    Sometimes you want to remind the LLM about specific tool usage
    patterns mid-conversation (e.g., if it's not using tools correctly).
    """
    
    prompts = {
        "web_search": """
When using web_search:
- Use clear, concise search queries (3-5 words)
- Focus on the main topic, avoid extra words
- Good: "weather Cairo Egypt"
- Bad: "Can you please tell me what the weather is like in Cairo, Egypt?"
""",
        
        "rag_query": """
When using rag_query:
- Use natural language questions
- Be specific about what information you're looking for
- Good: "project deadline and milestones"
- Bad: "stuff"
""",
        
        "gmail_draft": """
When drafting emails:
- Always include: recipient, subject, body
- Keep emails professional but friendly
- Use proper email structure (greeting, body, closing)
- Confirm with user before creating draft
"""
    }
    
    return prompts.get(tool_name, "")


def get_error_recovery_prompt(error_type: str) -> str:
    """
    Get prompts for handling specific error scenarios.
    
    Args:
        error_type: Type of error that occurred
    
    Returns:
        Prompt to help LLM recover gracefully
    
    Why this exists:
    When tools fail or errors occur, we can inject recovery instructions
    to help the LLM respond gracefully instead of just saying "error occurred."
    """
    
    prompts = {
        "tool_execution_failed": """
A tool execution failed. Acknowledge this gracefully and either:
1. Try a different approach (different tool or query)
2. Provide what information you can without the tool
3. Apologize and ask if there's another way to help

Don't just say "the tool failed" - be helpful and solution-oriented.
""",
        
        "api_rate_limit": """
You're experiencing rate limiting. Politely inform the user:
- Acknowledge the issue without technical jargon
- Suggest trying again in a moment
- Offer alternative ways to help that don't require API calls
""",
        
        "no_results_found": """
The search/query returned no results. Don't just say "no results."
Instead:
- Acknowledge what you searched for
- Suggest alternative search terms or approaches
- Ask if the user wants to try a different query
""",
        
        "ambiguous_query": """
The user's request is unclear. Ask a brief, specific clarifying question:
- Focus on the most important missing information
- Give examples if helpful
- Keep it conversational and friendly
"""
    }
    
    return prompts.get(error_type, "")


def get_summarization_prompt(content: str, max_words: int = 100) -> str:
    """
    Generate a prompt for summarizing content.
    
    Args:
        content: Content to summarize
        max_words: Maximum words in summary
    
    Returns:
        Prompt for summarization task
    
    Why this exists:
    - Used for "update my summary" command
    - Used to summarize long tool results
    - Used to condense conversation history when context limit is reached
    """
    
    return f"""Summarize the following content in {max_words} words or less.
Focus on key points, preferences, and important facts.
Write in concise, clear language. this summary should be used as user's preference for interacting with llm
so make it user oriented and conclusive.

Content:
{content}

Summary:"""


def get_conversation_starter_prompts() -> list[str]:
    """
    Get list of conversation starters the assistant can use.
    
    Returns:
        List of friendly opening messages
    
    Why this exists:
    When user first launches the assistant (or after long silence),
    the assistant can greet them naturally instead of just waiting silently.
    """
    
    return [
        "Hello! How can I help you today?",
        "Hi there! What can I do for you?",
        "Hey! I'm here to assist. What do you need?",
        "Good to see you! What's on your mind?",
        "Hello! Ready to help with whatever you need."
    ]


def format_rag_context(chunks: list) -> str:
    """
    Format RAG retrieval results for inclusion in LLM context.
    
    Args:
        chunks: List of retrieved text chunks from vector DB
            Format: [{"text": "...", "metadata": {...}}, ...]
        max_chunks: Maximum number of chunks to include
    
    Returns:
        Formatted string to add to messages
    
    """
    
    if not chunks:
        return "No relevant information found in user's documents."
    
    formatted = "Here's relevant information from the user's documents:\n\n"
    
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("text", "")
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", "Unknown source")
        page=metadata.get("page","")
        
        formatted += f"[Document {i} - {source}]\n{text} {'page No: ' if page else ''} {page if page else ''}\n\n"
    
    formatted += "Use this information to answer the user's query."
    
    return formatted


def format_web_search_results(results: list, max_results: int = 3) -> str:
    """
    Format web search results for inclusion in LLM context.
    
    Args:
        results: List of search results
            Format: [{"title": "...", "snippet": "...", "url": "..."}, ...]
        max_results: Maximum number of results to include
    
    Returns:
        Formatted string to add to messages
    
    """
    
    if not results:
        return "No search results found. The information may not be available online or the query needs refinement."
    
    # Limit number of results
    results = results[:max_results]
    
    formatted = "Here are the search results:\n\n"
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "No title")
        snippet = result.get("snippet", "No description available")
        url = result.get("url", "")
        
        formatted += f"{i}. {title}\n{snippet}\n"
        if url:
            formatted += f"Source: {url}\n"
        formatted += "\n"
    
    formatted += "Synthesize this information into a natural, concise response."
    
    return formatted


# Map of template names to functions
PROMPT_TEMPLATES = {
    "system": get_system_prompt,
    "tool_usage": get_tool_usage_prompt,
    "error_recovery": get_error_recovery_prompt,
    "summarization": get_summarization_prompt,
    "conversation_starters": get_conversation_starter_prompts,
}
