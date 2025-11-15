import numpy as np
import sounddevice as sd
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..audio import AudioRecorder, AudioPlayer, VoiceActivityDetector
from ..stt import FasterWhisperSTT
from ..tts import PiperTTS
from ..llm import OpenAIClient
from ..llm.prompts import get_system_prompt
from ..memory import SessionMemory, SessionManager, UserSummary, VectorDB
from ..tools.base import BaseTool, ToolRegistry
from ..tools.web_search import WebSearchTool
from ..tools.rag_query import RAGQueryTool
from ..tools.gmail_tool import GmailDraftTool
from ..tools.file_writer import FileWriterTool
from ..tools.save_info import SaveInfoTool
from ..tools.tool_selector import ToolSelector
from .command_router import CommandRouter, CommandHandlers
from .analytics import Analytics
from ..utils import get_logger, config

logger = get_logger(__name__)


class VoiceAssistant:
    """
    Main voice assistant orchestrator.
    """
    
    def __init__(self):
        """
        Initialize all components.
        
        Raises:
            Exception: If critical components fail to initialize
        """
        logger.info("=" * 70)
        logger.info("Initializing Voice Assistant...")
        logger.info("=" * 70)
        
        try:
            # Audio components
            print("🎤 Initializing audio...")

            self.recorder = AudioRecorder(sample_rate=config.AUDIO_SAMPLE_RATE)
            self.player = AudioPlayer(sample_rate=22050)  # Piper TTS sample rate
            self.vad = VoiceActivityDetector(
                sample_rate=config.AUDIO_SAMPLE_RATE,
                aggressiveness=config.VAD_AGGRESSIVENESS
            )
            
            # Speech processing
            print("🧠 Loading Whisper STT...")
            self.stt = FasterWhisperSTT()
            
            print("🗣️  Loading Piper TTS...")
            self.tts = PiperTTS()
            self.tts_speed = 1.0  # Default speed
            
            # LLM
            print("🤖 Connecting to OpenAI...")
            self.llm_client = OpenAIClient()
            
            # Memory systems
            print("💾 Initializing memory...")
            self.session_memory = SessionMemory()
            self.session_manager = SessionManager()
            self.user_summary = UserSummary()
            self.vector_db = VectorDB()
            
            # Tools
            print("🔧 Registering tools...")
            self.tool_registry = ToolRegistry()
            self._register_tools()
            
            # Tool selector (for smart tool picking)
            all_tools = [
                WebSearchTool(),
                RAGQueryTool(self.vector_db),
                GmailDraftTool(),
                FileWriterTool(),
                SaveInfoTool()
            ]
            self.tool_selector = ToolSelector(all_tools)
            
            # Command router
            self.command_router = CommandRouter()
            
            # Analytics
            self.analytics = Analytics()
            
            logger.info("✅ Voice Assistant initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Voice Assistant: {e}")
            raise
    
    def _register_tools(self):
        """Register all available tools."""
        # Always available tools
        self.tool_registry.register(SaveInfoTool())
        self.tool_registry.register(FileWriterTool())
        
        # Conditional tools (will be added dynamically via tool_selector)
        # - web_search
        # - rag_query
        # - gmail_draft
        
        logger.info(f"Registered {len(self.tool_registry.list_tools())} base tools")
    
    def process_turn(self, mode: str = 'press') -> bool:
        """
        Process one conversation turn.
        
        Args:
            mode: 'press' (press-to-speak) or 'vad' (voice activity)
        
        Returns:
            True to continue, False to exit
        
        Pipeline:
        1. Record audio
        2. Transcribe (STT)
        3. Display user input
        4. Check for exit command
        5. Route command OR call LLM
        6. Display assistant response
        7. Synthesize speech (TTS)
        8. Play audio
        9. Log analytics
        """
        try:
            # Step 1: Record audio
            print(f"\n{'='*70}")
            audio = self._record_audio(mode)
            
            if audio is None or len(audio) == 0:
                print("⚠️  No audio detected. Please try again.")
                return True
            
            # Step 2: Transcribe
            print("🤖 Transcribing...")
            result = self.stt.transcribe(audio)
            user_text = result["text"].strip()
            
            if not user_text:
                print("⚠️  No speech detected. Please try again.")
                return True
            
            # Step 3: Display user input
            print(f"\n🧑 User: {user_text}")
            
            # Step 4: Check for exit
            if self.command_router.is_exit_command(user_text):
                print("\n👋 Goodbye!")
                return False
            
            # Step 5: Route command or call LLM
            command = self.command_router.route(user_text)
            
            if command:
                # Handle special command
                response_text, should_speak, tts_speed = self._handle_command(command)
                
                # Update TTS speed if command changed it
                if tts_speed is not None:
                    self.tts_speed = tts_speed
                    self.player = AudioPlayer(sample_rate=22050*self.tts_speed) 

            else:
                # Pass to LLM with tools
                response_text, should_speak = self._process_with_llm(user_text)
            
            # Step 6: Display response
            if response_text:
                print(f"\n🤖 Assistant: {response_text}")
            
            # Step 7-8: TTS and playback
            if should_speak and response_text:
                print("🔊 Speaking...")
                self._speak(response_text)
            
            # Step 9: Log analytics
            self.analytics.log_message()
            
            return True
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            return False
        
        except Exception as e:
            logger.error(f"Error in process_turn: {e}")
            print(f"\n❌ Error: {str(e)}")
            print("   Please try again.")
            self.analytics.log_error()
            return True
    
    def _record_audio(self, mode: str) -> Optional[np.ndarray]:
        """
        Record audio based on mode.
        
        Args:
            mode: 'press' or 'vad'
        
        Returns:
            Audio numpy array or None
        """
        if mode == 'press':
            # Press-to-speak: Fixed 5 seconds
            input("\n⏺️  Press ENTER to speak (5 seconds)...")
            print("🎤 Recording... (5s)")
            
            audio = self.recorder.record_fixed_duration(5.0)
            return audio
        
        elif mode == 'vad':
            # Voice Activity Detection
            return self._vad_stream()
        
        else:
            raise ValueError(f"Unknown recording mode: {mode}")
    

    def _vad_stream(self):

        """
        Record audio using Voice Activity Detection with streaming.
        
        Returns:
            Audio numpy array or None
        
        Uses audio streaming callback for real-time processing.
        Listens continuously until speech detected → silence detected.
        """
        import queue
        import threading
        
        # Audio queue for streaming
        audio_queue = queue.Queue()
        
        # State variables
        self.vad.reset()
        speech_started = False
        speech_ended = False
        recorded_chunks = []
        
        # Timing
        frame_duration = 0.03  # 30ms for VAD
        blocksize = int(self.recorder.sample_rate * frame_duration)  # 480 samples
        max_recording_duration = 30.0  # seconds
        
        chunks_recorded = 0
        max_chunks = int(max_recording_duration / frame_duration)
        
        print("\n⏺️  Listening... (speak naturally, say 'exit' to stop)")
        
        def audio_callback(indata, frames, time_info, status):
            """Called by sounddevice for each audio block."""
            if status:
                logger.warning(f"Audio callback status: {status}")
            
            # Put audio data in queue
            audio_queue.put(indata.copy())
        
        # Start audio stream
        try:
            with sd.InputStream(
                samplerate=self.recorder.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=blocksize,
                callback=audio_callback
            ):
                print("🎤 [Ready - waiting for speech...]", end='\r')
                
                while not speech_ended and chunks_recorded < max_chunks:
                    try:
                        # Get audio chunk from queue (timeout to allow checking stop condition)
                        chunk = audio_queue.get(timeout=0.1)
                        chunk = chunk.flatten()
                        
                        # Process with VAD
                        started, ended = self.vad.process_frame(chunk)
                        
                        if started:
                            speech_started = True
                            print("🎤 [Speech detected - recording...]", end='\r')
                        
                        if speech_started:
                            recorded_chunks.append(chunk)
                            chunks_recorded += 1
                            
                            # Show progress every 0.5s
                            if chunks_recorded % 16 == 0:
                                duration = chunks_recorded * frame_duration
                                bar = '█' * min(20, int(duration / 1.5)) + '░' * max(0, 20 - int(duration / 1.5))
                                print(f"🎤 Recording... [{bar}] {duration:.1f}s", end='\r')
                        
                        if ended:

                            speech_ended = True
                            # check power and remove padding from power calculation. padding frames = 750/30 = 25
                            arr = np.array(recorded_chunks[:-25])
                            arr = arr.flatten()
                            if np.mean(arr**2) < 0.001:
                                self.vad.reset()
                                speech_started = False
                                speech_ended = False
                                recorded_chunks=[]
                                chunks_recorded=0
                                audio_queue = queue.Queue()
                                continue
                            else:
                                print("\n✅ Speech ended (silence detected)")
                                break
                    
                    except queue.Empty:
                        # No audio data yet, continue
                        continue
                
                # Check if we got any speech
                if not speech_started:
                    print("\n⚠️  No speech detected")
                    return None
                
                if chunks_recorded >= max_chunks:
                    print(f"\n⚠️  Max recording duration ({max_recording_duration}s) reached")
                
                # Concatenate all chunks
                if recorded_chunks:
                    audio = np.concatenate(recorded_chunks)
                    
                    if len(audio) < self.recorder.sample_rate * 0.3:
                        print("\n⚠️  Recording too short")
                        return None
                    elif audio.max() < 0.08:
                        return None
                    
                    print(f"✅ Recorded {len(audio) / self.recorder.sample_rate:.1f}s")
                    return audio
                else:
                    print("\n⚠️  No audio recorded")
                    return None
        
        except KeyboardInterrupt:
            print("\n⚠️  Recording interrupted")
            return None
        except Exception as e:
            logger.error(f"Streaming VAD error: {e}")
            print(f"\n❌ Recording error: {str(e)}")
            return None


    def _handle_command(self, command: Dict[str, Any]) -> tuple:
        """
        Handle special command.
        
        Args:
            command: Command dict from router
        
        Returns:
            (response_text, should_speak, tts_speed)
        """
        command_name = command["command"]
  
        
        logger.info(f"Handling command: {command_name}")
        
        if command_name == 'save_session':
            name = input("Enter session name :   ")
            
        
        # Map command to handler
        handlers = {
            "save_session": lambda: CommandHandlers.save_session_with_name(
                self.session_memory, self.session_manager, 
                self.user_summary, self.llm_client,name=name
            ),
            "load_session": lambda: CommandHandlers.load_session_by_choice(
                self.session_memory, self.session_manager , choice=None
            ),
            "list_sessions": lambda: CommandHandlers.handle_list_sessions(
                self.session_manager
            ),
            "delete_session": lambda: CommandHandlers.handle_delete_session(
                self.session_manager
            ),
            "clear_conversation": lambda: CommandHandlers.handle_clear_conversation(
                self.session_memory
            ),
            "speak_slower": lambda: CommandHandlers.handle_speak_slower(),
            "speak_faster": lambda: CommandHandlers.handle_speak_faster(),
            "speak_normal": lambda: CommandHandlers.handle_speak_normal()
        }
        
        handler = handlers.get(command_name)
        
        if handler:
            return handler()
        else:
            logger.error(f"Unknown command: {command_name}")
            return ("❌ Unknown command", False, None)
    
    def _process_with_llm(self, user_text: str) -> tuple:
        """
        Process user input with LLM and tools.
        
        Args:
            user_text: User's transcribed speech
        
        Returns:
            (response_text, should_speak=True)
        """
        # Add user message to memory
        self.session_memory.add_message("user", user_text)
        
        # Get system prompt with user summary
        user_summary_text = self.user_summary.load()
        system_prompt = get_system_prompt(user_summary=user_summary_text)
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            *self.session_memory.get_messages_for_llm()
        ]
        
        # Select relevant tools based on context
        recent_messages = self.session_memory.get_last_n_messages(5)
        selected_tools = self.tool_selector.select_tools(
            recent_messages=recent_messages,
            include_all=False  # Smart selection
        )
        
        # Get tool schemas
        tool_schemas = [tool.get_openai_tool_schema() for tool in selected_tools]
        
        logger.info(f"Selected {len(selected_tools)} tools: {[t.name for t in selected_tools]}")
        
        try:
            # Call LLM with function calling
            print("🤖 Thinking...")
            
            response ,tokens = self.llm_client.execute_tool_call_loop(
                messages=messages,
                tools=tool_schemas,
                tool_executor=self._execute_tool,
                max_iterations=5
            )
            self.analytics.log_tokens(tokens)
            
            # Extract response text
            assistant_text = response.get("content", "")
            
            # Add to memory
            self.session_memory.add_message(
                "assistant", 
                assistant_text,
                tool_calls=response.get("tool_calls")
            )
            
            return (assistant_text, True)
        
        except Exception as e:
            logger.error(f"LLM error: {e}")
            self.analytics.log_error()
            
            error_msg = "I'm sorry, I encountered an error processing your request. Please try again."
            self.session_memory.add_message("assistant", error_msg)
            
            return (error_msg, True)
    
    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
        
        Returns:
            Tool result as string
        """
        logger.info(f"Executing tool: {tool_name}({arguments})")
        print(f"   🔧 [{tool_name}]...")
        
        # Log for analytics
        self.analytics.log_tool_use(tool_name)
        
        # Get tool from selector (includes conditional tools)
        tool = self.tool_selector.all_tools.get(tool_name)
        
        if not tool:
            # Try base registry
            tool = self.tool_registry.get_tool(tool_name)
        
        if not tool:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        
        try:
            result = tool.execute(**arguments)
            logger.info(f"Tool {tool_name} completed")
            return result
        
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(error_msg)
            self.analytics.log_error()
            return f"Error: {error_msg}"
    
    def _speak(self, text: str):
        """
        Synthesize speech and play it.
        
        Args:
            text: Text to speak
        """
        try:
            # Synthesize
            audio = self.tts.synthesize(text)
            
            if audio is None or len(audio) == 0:
                logger.warning("TTS returned empty audio")
                return
            
            # Play (blocking)
            self.player.play(audio, blocking=True)

        except KeyboardInterrupt :
            print()
        
        except Exception as e:
            logger.error(f"TTS/playback error: {e}")
            print(f"⚠️  Could not play audio: {str(e)}")
    
    def start_session(self):
        """Start a new session (for analytics)."""
        self.analytics.start_session()
        logger.info("Session started")
    
    def end_session(self):
        """End current session (for analytics)."""
        self.analytics.end_session()
        logger.info("Session ended")
    
    def get_session_count(self) -> int:
        """Get number of saved sessions."""
        return self.session_manager.get_session_count()
    
    def list_sessions(self) -> List[Dict]:
        """Get list of saved sessions."""
        return self.session_manager.list_sessions(limit=50)