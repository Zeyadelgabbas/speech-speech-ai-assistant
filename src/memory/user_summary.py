"""
User summary management - stores user profile, preferences, and key facts.
This is the persistent "who is the user" memory that persists across all sessions.
"""
from pathlib import Path
from typing import Optional
from ..utils import get_logger , config

logger = get_logger(__name__)


class UserSummary:
    """
    Manages the user summary file (user_summary.txt).
    
    This stores:
    - User preferences (e.g., "prefers concise responses")
    - User profile (e.g., "works as software engineer in Cairo")
    - Important facts (e.g., "allergic to peanuts", "has 2 kids")
    
    Unlike session memory (which is cleared), this persists forever
    and is loaded at the start of every conversation.
    
    Think of it as the assistant's "long-term memory" about the user.
    """
    
    def __init__(self, summary_file: Optional[Path] = None):
        """
        Initialize user summary manager.
        
        Args:
            summary_file: Path to summary file. If None, uses config.USER_SUMMARY_FILE
        """
        self.summary_file = summary_file or config.USER_SUMMARY_FILE
        
        # Ensure parent directory exists
        self.summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty file if doesn't exist
        if not self.summary_file.exists():
            self._create_default_summary()
        
        logger.info(f"UserSummary initialized: {self.summary_file}")
    
    def _create_default_summary(self):
        """Create a default summary file with template."""
        default_content = """# User Summary

## Preferences
- (No preferences set yet)

## Profile
- (No profile information yet)

## Important Facts
- (No important facts yet)

"""
        self.summary_file.write_text(default_content.strip())
        logger.info("Created default user summary file")
    
    def load(self) -> str:
        """
        Load the user summary from file.
        
        Returns:
            Summary content as string (empty string if file doesn't exist or is empty)
        
        Why this method exists:
        The summary is loaded at the start of every session and included
        in the system prompt, so the LLM knows about the user.
        """
        try:
            if not self.summary_file.exists():
                logger.warning("User summary file doesn't exist, creating default")
                self._create_default_summary()
            
            content = self.summary_file.read_text(encoding='utf-8').strip()
            
            if not content:
                logger.warning("User summary file is empty")
                return ""
            
            logger.info(f"Loaded user summary: {len(content)} characters")
            return content
        
        except Exception as e:
            logger.error(f"Error loading user summary: {e}")
            return ""
    
    def save(self, content: str):
        """
        Save updated summary to file.
        
        Args:
            content: New summary content
        
        Why this method exists:
        When user says "update my summary", we:
        1. Ask LLM to summarize the current session
        2. Append the summary to existing content
        3. Save it back to file
        """
        try:
            # Ensure content is not empty
            if not content.strip():
                logger.warning("Attempted to save empty summary, ignoring")
                return
            
            self.summary_file.write_text(content.strip(), encoding='utf-8')
            logger.info(f"Saved user summary: {len(content)} characters")
            print("✅ User summary updated")
        
        except Exception as e:
            logger.error(f"Error saving user summary: {e}")
            raise
    
    def append(self, new_content: str):
        """
        Append new content to existing summary.
        
        Args:
            new_content: Content to append (e.g., session summary)
        
        Why this method exists:
        When user says "update my summary", we don't want to overwrite
        the entire file - we append new insights from the current session.
        
        Example:
            Existing: "User prefers concise responses."
            New: "User is working on AI project with Python."
            Result: Both pieces of info are preserved.
        """
        try:
            existing = self.load()
            
            # Add separator if file already has content
            if existing:
                combined = f"{existing}\n\n---\n\n{new_content.strip()}"
            else:
                combined = new_content.strip()
            
            self.save(combined)
            logger.info("Appended to user summary")
        
        except Exception as e:
            logger.error(f"Error appending to user summary: {e}")
            raise
    
    def clear(self):
        """
        Clear the summary file (reset to default).
        
        Why this method exists:
        Allows user to "start fresh" if they want to reset their profile.
        Could be triggered by voice command "clear my summary" or CLI.
        """
        try:
            self._create_default_summary()
            logger.info("User summary cleared (reset to default)")
            print("✅ User summary cleared")
        
        except Exception as e:
            logger.error(f"Error clearing user summary: {e}")
            raise
    
    def get_summary_length(self) -> int:
        """
        Get the character count of the summary.
        
        Returns:
            Number of characters in summary
        
        Why this method exists:
        Monitor summary size to ensure it doesn't grow too large.
        If summary exceeds ~5000 chars, might need to condense it.
        """
        content = self.load()
        return len(content)
    
    def is_empty(self) -> bool:
        """
        Check if summary file is empty or contains only default template.
        
        Returns:
            True if empty/default, False if has user content
        """
        content = self.load()
        
        # Consider empty if no content or only default template
        is_empty = (
            not content or
            "No preferences set yet" in content or
            len(content) < 100
        )
        
        return is_empty
