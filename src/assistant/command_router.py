from typing import Optional, Dict, Any, Tuple
import re
from ..utils import get_logger

logging = get_logger(__name__)


class CommandRouter:
    """
    Routes special voice commands to appropriate handlers.
    """
    
    def __init__(self):
        """Initialize command router."""
        # Command patterns (regex for flexibility)
        self.patterns = {
            # Session management (NO NAME CAPTURE - prompt via CLI)
            "save_session": r"save\s+(?:this\s+)?session",
            "load_session": r"load\s+(?:a\s+)?session",
            "list_sessions": r"list\s+(?:my\s+)?sessions?",
            "delete_session": r"delete\s+session\s+(.+)",
            "clear_conversation": r"clear\s+conversation",
            
            # TTS speed control
            "speak_slower": r"speak\s+slower",
            "speak_faster": r"speak\s+faster",
            "speak_normal": r"speak\s+normal(?:\s+speed)?",
            
            # Exit/stop
            "stop_listening": r"stop\s+listening"
        }
        
        logging.info("CommandRouter initialized")
    
    def route(self, user_text: str) -> Optional[Dict[str, Any]]:
        """
        Check if user text matches a special command.
        
        Args:
            user_text: Transcribed user speech
        
        Returns:
            Command dict if matched, None if should pass to LLM
            
            Format: {
                "command": "save_session",
                "args": {...},
                "handler": "handle_save_session"
            }
        """
        # Normalize input
        normalized = user_text.lower().strip()
        
        logging.debug(f"Routing: '{normalized}'")
        
        # Try each pattern
        for command_name, pattern in self.patterns.items():
            match = re.search(pattern, normalized)
            
            if match:
                # Extract arguments from regex groups
                args = self._extract_args(command_name, match)
                
                logging.info(f"Command matched: {command_name} with args: {args}")
                
                return {
                    "command": command_name,
                    "args": args,
                    "handler": f"handle_{command_name}"
                }
        
        # No command matched
        logging.debug("No command matched, passing to LLM")
        return None
    
    def _extract_args(self, command_name: str, match: re.Match) -> Dict[str, Any]:
        """
        Extract arguments from regex match groups.
        
        Args:
            command_name: Name of matched command
            match: Regex match object
        
        Returns:
            Dictionary of arguments
        """
        args = {}
        
        # Only delete_session has name in pattern
        if command_name == "delete_session":
            if match.groups():
                name = match.group(1).strip()
                args["name"] = name
        
        # save_session and load_session: no args (prompt via CLI)
        
        return args
    
    def is_exit_command(self, user_text: str) -> bool:
        """
        Check if user wants to exit.
        
        Args:
            user_text: User input
        
        Returns:
            True if exit command detected
        
        Exit commands: "exit", "quit", "goodbye", "bye"
        """
        normalized = user_text.lower().strip()
        exit_keywords = ["exit", "quit", "goodbye", "bye", "stop"]
        
        return any(keyword == normalized for keyword in exit_keywords)


# ============================================================================
# COMMAND HANDLERS (Called by VoiceAssistant)
# ============================================================================

class CommandHandlers:
    """
    Handlers for special commands.
    
    Each handler returns a tuple: (response_text, should_speak, tts_speed)
    - response_text: What to display/say to user
    - should_speak: Whether to use TTS (False for system messages)
    - tts_speed: TTS speed (only for speak_* commands)
    """
    # Initialize tts speed = 1.0 
    tts_speed = 1.0
        
    @staticmethod
    def handle_save_session(session_memory, session_manager, user_summary, llm_client) -> Tuple[str, bool, Optional[float]]:
        """
        Save current session - NAME WILL BE PROMPTED VIA CLI.
        
        Returns:
            ("PROMPT_NAME", False, None) - signals main.py to prompt for name
        """
        # Signal to main.py: prompt user for name via CLI
        return ("PROMPT_NAME", False, None)
    
    @staticmethod
    def save_session_with_name(session_memory, session_manager, user_summary, llm_client, name: str) -> Tuple[str, bool, Optional[float]]:
        """
        Actually save the session with provided name.
        
        Called by main.py after getting name from user.
        """
        try:
            session_data = session_memory.to_dict()
            
            # Save to database
            session_id = session_manager.save_session(name, session_data)
            
            # Update user summary if enough messages
            if session_memory.get_message_count() >= 5:
                recent_messages = session_memory.get_last_n_messages(10)
                
                conversation_text = "\n".join([
                    f"{msg['role']}: {msg.get('content', '')}" 
                    for msg in recent_messages if msg.get('content')
                ])
                
                summary_prompt = f"""Summarize this conversation into 2-3 bullet points focusing on:
- User preferences revealed
- Important facts about the user
- Topics the user is interested in

Conversation:
{conversation_text}

Summary (2-3 bullet points):"""
                
                try:
                    summary_response = llm_client.chat([
                        {"role": "user", "content": summary_prompt}
                    ])
                    
                    session_summary = summary_response["content"]
                    
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d")
                    
                    user_summary.append(f"\n## Session: {name} ({timestamp})\n{session_summary}")
                    
                    logging.info(f"Session '{name}' saved and summary updated")
                    
                except Exception as e:
                    logging.error(f"Failed to update user summary: {e}")
            
            return (
                f"✅ Session '{name}' saved successfully!\n"
                f"   Messages: {session_data['message_count']}\n"
                f"   Duration: {session_data.get('duration', 'N/A')}\n"
                f"   User summary updated.",
                False,
                None
            )
        
        except Exception as e:
            logging.error(f"Failed to save session: {e}")
            return (f"❌ Error saving session: {str(e)}", False, None)
    
    @staticmethod
    def handle_load_session(session_memory, session_manager) -> Tuple[str, bool, Optional[float]]:
        """
        Load session - LIST WILL BE SHOWN VIA CLI.
        
        Returns:
            ("PROMPT_LOAD", False, None) - signals main.py to show session list
        """
        # Signal to main.py: show session list and prompt
        return ("PROMPT_LOAD", False, None)
    
    @staticmethod
    def load_session_by_choice(session_memory, session_manager, choice: str) -> Tuple[str, bool, Optional[float]]:
        """
        Actually load the session by user's numeric choice.
        
        Called by main.py after user selects from list.
        """
        try:
            #@@@@@@@@@@@@@@@@@
            if choice is None:
                logging.info("Choice is None")
                CommandHandlers.handle_list_sessions(session_manager=session_manager)
                choice = input("Please enter the required session to load : ")
            if not choice.isdigit():
                return ("❌ Invalid choice. Must be a number.", False, None)
            
            session_id = int(choice)
            
            # Get session list to map number to actual session
            #@@@@@@@@@@@
            sessions = session_manager.list_sessions(limit=50)
            
            if session_id < 1 or session_id > len(sessions):
                return (f"❌ Invalid session number. Choose 1-{len(sessions)}.", False, None)
            
            # Load the selected session
            selected = sessions[session_id - 1]
            session_data = session_manager.load_session(selected['name'])
            
            if not session_data:
                return (f"❌ Failed to load session.", False, None)
            
            # Restore session
            session_memory.from_dict(session_data)
            
            logging.info(f"Loaded session '{session_data['name']}' with {session_data['message_count']} messages")
            
            response = f"✅ Loaded session: {session_data['name']}\n"
            response += f"   Messages: {session_data['message_count']}\n"
            response += f"   Created: {session_data['created_at'][:10]}\n\n"
            response += "📜 Previous conversation restored."
            
            return (response, False, None)
        
        except Exception as e:
            logging.error(f"Failed to load session: {e}")
            return (f"❌ Error loading session: {str(e)}", False, None)
    
    @staticmethod
    def handle_list_sessions(session_manager) -> Tuple[str, bool, Optional[float]]:
        """List all saved sessions."""
        try:
            sessions = session_manager.list_sessions(limit=10)
            
            if not sessions:
                return ("📚 No saved sessions yet.", False, None)
            
            response = f"📚 You have {len(sessions)} saved session(s):\n\n"
            
            for i, session in enumerate(sessions, 1):
                response += f"   [{i}] {session['name']}\n"
                response += f"       {session['message_count']} messages, {session['created_at'][:10]}\n"
            
            response += "\n💡 Say 'load session' to resume a session."
            
            return (response, False, None)
        
        except Exception as e:
            logging.error(f"Failed to list sessions: {e}")
            return (f"❌ Error listing sessions: {str(e)}", False, None)
    
    @staticmethod
    def handle_delete_session(session_manager, name: str) -> Tuple[str, bool, Optional[float]]:
        """Delete a session by name."""
        try:
            success = session_manager.delete_session(name)
            
            if success:
                return (f"✅ Session '{name}' deleted successfully.", False, None)
            else:
                return (f"❌ Session '{name}' not found.", False, None)
        
        except Exception as e:
            logging.error(f"Failed to delete session: {e}")
            return (f"❌ Error deleting session: {str(e)}", False, None)
    
    @staticmethod
    def handle_clear_conversation(session_memory) -> Tuple[str, bool, Optional[float]]:
        """Clear current conversation."""
        message_count = session_memory.get_message_count()
        session_memory.clear()
        
        logging.info(f"Cleared conversation ({message_count} messages removed)")
        
        return (
            f"✅ Conversation cleared ({message_count} messages removed).\n"
            "   User summary preserved.",
            False,
            None
        )
    
    @staticmethod
    def handle_speak_slower() -> Tuple[str, bool, Optional[float]]:
        """Slows tts speed"""
        speeds = [2,1.75,1.5,1.25,1.0,0.75,0.5,0.25]
        idx = speeds.index(CommandHandlers.tts_speed)
        if idx == len(speeds)-1:
            return (f"This is the slowest speed", True, 0.25)
        new_speed = speeds[idx+1]
        CommandHandlers.tts_speed = new_speed
        
        return (f"I'll speak slower. changed speed to : {new_speed}", True, new_speed)
    
    @staticmethod
    def handle_speak_faster() -> Tuple[str, bool, Optional[float]]:
        """Set TTS speed to 1.25x."""
        speeds = [2.0,1.75,1.5,1.25,1.0,0.75,0.5,0.25]
        idx = speeds.index(CommandHandlers.tts_speed)
        if idx == 0 :
            return (f"This is the fastest speed", True, 2.0)
        new_speed = speeds[idx-1]
        CommandHandlers.tts_speed = new_speed
        
        return (f"I'll speak faster. changed speed to : {new_speed}", True, new_speed)
    
    @staticmethod
    def handle_speak_normal() -> Tuple[str, bool, Optional[float]]:
        """Reset TTS speed to 1.0x."""
        return ("Back to normal speed.", True, 1.0)