import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.assistant.voice_assistant import VoiceAssistant
from src.assistant.command_router import CommandHandlers
from src.utils import get_logger, config

logger = get_logger(__name__)


def print_banner():
    """Display startup banner."""
    print("\n" + "=" * 70)
    print("                    🎤 VOICE AI ASSISTANT v1.0")
    print("=" * 70 + "\n")


def startup_menu(assistant: VoiceAssistant) -> str:
    """
    Display startup menu and get user choice.
    
    Args:
        assistant: VoiceAssistant instance
    
    Returns:
        Choice: 'new', 'load:<number>', 'delete', 'stats', 'exit'
    """
    # Show saved sessions
    sessions = assistant.list_sessions()
    
    if sessions:
        print("📚 Saved Sessions:")
        print("-" * 70)
        for i, session in enumerate(sessions[:10], 1):
            print(f"   [{i}] {session['name']}")
            print(f"       {session['message_count']} messages, {session['created_at'][:10]}")
        print("-" * 70)
        print("\n💡 Options:")
        print("   • Type session number (1-10) to load")
        print("   • Press ENTER for new session")
        print("   • Type 'delete' to manage sessions")
        print("   • Type 'stats' for usage statistics")
        print("   • Type 'exit' to quit")
    else:
        print("📚 No saved sessions yet.")
        print("\n💡 Options:")
        print("   • Press ENTER to start new session")
        print("   • Type 'stats' for usage statistics")
        print("   • Type 'exit' to quit")
    
    choice = input("\nChoice: ").strip().lower()
    
    # Handle choices
    if not choice:
        return 'new'
    elif choice == 'exit':
        return 'exit'
    elif choice == 'delete':
        return 'delete'
    elif choice == 'stats':
        return 'stats'
    elif choice.isdigit():
        session_num = int(choice)
        if 1 <= session_num <= len(sessions):
            return f'load:{session_num}'
        else:
            print(f"❌ Invalid session number. Choose 1-{len(sessions)}.")
            return startup_menu(assistant)
    else:
        print("❌ Invalid choice. Please try again.")
        return startup_menu(assistant)


def delete_menu(assistant: VoiceAssistant):
    """
    Session deletion management menu.
    
    Args:
        assistant: VoiceAssistant instance
    """
    while True:
        print("\n" + "=" * 70)
        print("                    SESSION MANAGEMENT")
        print("=" * 70)
        
        sessions = assistant.list_sessions()
        
        if not sessions:
            print("\n📚 No saved sessions.")
            input("\nPress ENTER to return...")
            return
        
        print("\nYour saved sessions:")
        print("-" * 70)
        for i, session in enumerate(sessions, 1):
            print(f"   [{i}] {session['name']}")
            print(f"       {session['message_count']} messages, {session['created_at'][:10]}")
        print("-" * 70)
        
        print("\n💡 Options:")
        print("   • Type number to DELETE session")
        print("   • Type 'all' to delete ALL sessions")
        print("   • Type 'back' to return")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == 'back':
            return
        elif choice == 'all':
            confirm = input("⚠️  Delete ALL sessions? Type 'yes' to confirm: ").strip().lower()
            if confirm == 'yes':
                for session in sessions:
                    assistant.session_manager.delete_session(session['name'])
                print("✅ All sessions deleted.")
                input("\nPress ENTER to continue...")
                return
            else:
                print("❌ Cancelled.")
        elif choice.isdigit():
            session_num = int(choice)
            if 1 <= session_num <= len(sessions):
                selected = sessions[session_num - 1]
                confirm = input(f"⚠️  Delete '{selected['name']}'? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    assistant.session_manager.delete_session(selected['name'])
                    print(f"✅ Session '{selected['name']}' deleted.")
                    input("\nPress ENTER to continue...")
                else:
                    print("❌ Cancelled.")
            else:
                print(f"❌ Invalid number. Choose 1-{len(sessions)}.")
        else:
            print("❌ Invalid choice.")


def show_stats(assistant: VoiceAssistant):
    """
    Display usage statistics.
    
    Args:
        assistant: VoiceAssistant instance
    """
    print("\n")
    report = assistant.analytics.generate_report()
    print(report)
    input("\nPress ENTER to continue...")


def mode_selection_menu() -> str:
    """
    Select recording mode.
    
    Returns:
        Mode: 'press' or 'vad'
    """
    print("\n" + "=" * 70)
    print("                      SELECT MODE")
    print("=" * 70)
    print("\n  [1] 🎙️  Press-to-Speak (5 seconds, precise control)")
    print("  [2] 🔊 Voice Activity Detection (hands-free, natural flow)")
    print("  [3] 🚪 Exit")
    print("\n" + "=" * 70)
    
    while True:
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            return 'press'
        elif choice == '2':
            return 'vad'
        elif choice == '3':
            return 'exit'
        else:
            print("❌ Invalid choice. Choose 1, 2, or 3.")


def main_loop(assistant: VoiceAssistant, mode: str):
    """
    Main conversation loop.
    
    Args:
        assistant: VoiceAssistant instance
        mode: Recording mode ('press' or 'vad')
    """
    print("\n" + "=" * 70)
    print(f"🔊 Mode: {'Press-to-Speak' if mode == 'press' else 'Voice Activity Detection'}")
    print("=" * 70)
    
    if mode == 'vad':
        print("\n💡 Tips:")
        print("   • Speak naturally, I'll detect when you start/stop")
        print("   • Say 'exit' or 'quit' to end conversation")
        print("   • Say 'save session' to save this conversation")
    else:
        print("\n💡 Tips:")
        print("   • Press ENTER, then speak for 5 seconds")
        print("   • Say 'exit' or 'quit' to end conversation")
        print("   • Say 'save session' to save this conversation")
    
    # Start analytics tracking
    assistant.start_session()
    
    try:
        while True:
            # Process one turn
            continue_conversation = assistant.process_turn(mode)
            
            # Check if we should continue
            if not continue_conversation:
                break
            
            # Check for special command responses (PROMPT_NAME, PROMPT_LOAD)
            last_response = assistant.session_memory.get_last_n_messages(1)
            if last_response and last_response[0].get("role") == "assistant":
                content = last_response[0].get("content", "")
                
                if content == "PROMPT_NAME":
                    # User said "save session" - prompt for name
                    handle_save_session_prompt(assistant)
                
                elif content == "PROMPT_LOAD":
                    # User said "load session" - show menu
                    handle_load_session_prompt(assistant)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    finally:
        # End analytics tracking
        assistant.end_session()


def handle_save_session_prompt(assistant: VoiceAssistant):
    """
    Prompt user to input session name and save.
    
    Args:
        assistant: VoiceAssistant instance
    """
    print("\n" + "=" * 70)
    print("                    SAVE SESSION")
    print("=" * 70)
    
    name = input("\nEnter session name: ").strip()
    
    if not name:
        print("❌ Session name cannot be empty. Save cancelled.")
        return
    
    # Check if name exists
    if assistant.session_manager.session_exists(name):
        confirm = input(f"⚠️  Session '{name}' already exists. Overwrite? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Save cancelled.")
            return
    
    # Save the session
    print("\n💾 Saving session...")
    response, _, _ = CommandHandlers.save_session_with_name(
        assistant.session_memory,
        assistant.session_manager,
        assistant.user_summary,
        assistant.llm_client,
        name
    )
    
    print(response)
    print("\n" + "=" * 70)


def handle_load_session_prompt(assistant: VoiceAssistant):
    """
    Show session list and prompt user to select.
    
    Args:
        assistant: VoiceAssistant instance
    """
    print("\n" + "=" * 70)
    print("                    LOAD SESSION")
    print("=" * 70)
    
    sessions = assistant.list_sessions()
    
    if not sessions:
        print("\n📚 No saved sessions yet.")
        input("\nPress ENTER to continue...")
        return
    
    print("\nSaved sessions:")
    print("-" * 70)
    for i, session in enumerate(sessions, 1):
        print(f"   [{i}] {session['name']}")
        print(f"       {session['message_count']} messages, {session['created_at'][:10]}")
    print("-" * 70)
    
    choice = input("\nEnter session number (or 'cancel'): ").strip().lower()
    
    if choice == 'cancel':
        print("❌ Load cancelled.")
        return
    
    if not choice.isdigit():
        print("❌ Invalid choice. Must be a number.")
        return
    
    # Load the session
    print("\n📂 Loading session...")
    response, _, _ = CommandHandlers.load_session_by_choice(
        assistant.session_memory,
        assistant.session_manager,
        choice
    )
    
    print(response)
    print("\n" + "=" * 70)


def main():
    """
    Main entry point.
    
    Flow:
    1. Display banner
    2. Validate configuration
    3. Initialize assistant
    4. Show startup menu (load/new/delete/stats)
    5. Select mode (press/vad)
    6. Run main loop
    7. Cleanup
    """
    try:
        # Print banner
        print_banner()
        
        # Validate config
        print("⚙️  Validating configuration...")
        config.validate_config()
        print()
        
        # Initialize assistant
        print("🚀 Initializing Voice Assistant...")
        print("-" * 70)
        assistant = VoiceAssistant()
        print("-" * 70)
        print("✅ Ready!")
        
        # Main application loop
        while True:
            # Startup menu
            choice = startup_menu(assistant)
            
            if choice == 'exit':
                print("\n👋 Goodbye!")
                break
            
            elif choice == 'delete':
                delete_menu(assistant)
                continue
            
            elif choice == 'stats':
                show_stats(assistant)
                continue
            
            elif choice.startswith('load:'):
                # Load session
                session_num = choice.split(':')[1]
                print(f"\n📂 Loading session {session_num}...")
                
                response, _, _ = CommandHandlers.load_session_by_choice(
                    assistant.session_memory,
                    assistant.session_manager,
                    session_num
                )
                
                print(response)
                
                # Continue to mode selection
                mode = mode_selection_menu()
                if mode == 'exit':
                    continue
                
                # Run conversation
                main_loop(assistant, mode)
            
            elif choice == 'new':
                # New session
                mode = mode_selection_menu()
                if mode == 'exit':
                    continue
                
                # Run conversation
                main_loop(assistant, mode)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("👋 Goodbye!")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {str(e)}")
        print("   Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()