"""
Integration test - Verify all components work together.
Run this before launching the full application.
"""
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test all imports work."""
    print("=" * 70)
    print("TEST 1: Imports")
    print("=" * 70)
    
    try:
        # Core modules
        from src.audio import AudioRecorder, AudioPlayer, VoiceActivityDetector
        from src.stt import FasterWhisperSTT
        from src.tts import PiperTTS
        from src.llm import OpenAIClient
        from src.memory import SessionMemory, SessionManager, UserSummary, VectorDB
        from src.tools.base import ToolRegistry
        from src.tools import web_search, rag_query, gmail_tool, file_writer, save_info
        from src.assistant import VoiceAssistant, CommandRouter, Analytics
        from src.utils import config, get_logger
        
        print("✅ All imports successful")
        return True
    
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config():
    """Test configuration is valid."""
    print("\n" + "=" * 70)
    print("TEST 2: Configuration")
    print("=" * 70)
    
    try:
        from src.utils import config
        
        # Check critical config
        assert config.OPENAI_API_KEY, "OPENAI_API_KEY not set"
        assert not config.OPENAI_API_KEY.startswith("sk-proj-xxx"), "OPENAI_API_KEY is placeholder"
        
        print(f"✅ OpenAI API Key: {config.OPENAI_API_KEY[:10]}...")
        print(f"✅ Whisper Model: {config.WHISPER_MODEL_SIZE}")
        print(f"✅ TTS Voice: {config.PIPER_VOICE}")
        
        return True
    
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False


def test_audio():
    """Test audio I/O."""
    print("\n" + "=" * 70)
    print("TEST 3: Audio I/O")
    print("=" * 70)
    
    try:
        from src.audio import AudioRecorder, AudioPlayer
        import numpy as np
        
        # Test recorder
        recorder = AudioRecorder()
        print("✅ AudioRecorder initialized")
        
        # Test player
        player = AudioPlayer(sample_rate=22050)
        print("✅ AudioPlayer initialized")
        
        # Test playback (1 second of sine wave)
        print("   Testing playback...")
        t = np.linspace(0, 1, 22050, endpoint=False)
        audio = 0.2 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        player.play(audio, blocking=True)
        print("✅ Playback successful")
        
        return True
    
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False


def test_stt():
    """Test STT initialization."""
    print("\n" + "=" * 70)
    print("TEST 4: Speech-to-Text")
    print("=" * 70)
    
    try:
        from src.stt import FasterWhisperSTT
        
        print("   Loading Whisper model (may take a minute)...")
        stt = FasterWhisperSTT()
        print("✅ Whisper loaded successfully")
        
        return True
    
    except Exception as e:
        print(f"❌ STT test failed: {e}")
        return False


def test_tts():
    """Test TTS initialization."""
    print("\n" + "=" * 70)
    print("TEST 5: Text-to-Speech")
    print("=" * 70)
    
    try:
        from src.tts import PiperTTS
        
        print("   Loading Piper TTS...")
        tts = PiperTTS()
        print("✅ Piper TTS loaded successfully")
        
        # Test synthesis
        print("   Testing synthesis...")
        audio = tts.synthesize("Hello, this is a test.")
        assert len(audio) > 0, "TTS returned empty audio"
        print(f"✅ Synthesized {len(audio)} samples")
        
        return True
    
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False


def test_llm():
    """Test LLM connection."""
    print("\n" + "=" * 70)
    print("TEST 6: Language Model")
    print("=" * 70)
    
    try:
        from src.llm import OpenAIClient
        
        client = OpenAIClient()
        print("✅ OpenAI client initialized")
        
        # Test simple chat
        print("   Testing API call...")
        response = client.chat([
            {"role": "user", "content": "Say 'test successful' and nothing else."}
        ])
        
        assert response["content"], "Empty response from LLM"
        print(f"✅ LLM response: {response['content'][:50]}...")
        
        return True
    
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False


def test_memory():
    """Test memory systems."""
    print("\n" + "=" * 70)
    print("TEST 7: Memory Systems")
    print("=" * 70)
    
    try:
        from src.memory import SessionMemory, SessionManager, UserSummary, VectorDB
        
        # Session memory
        session_memory = SessionMemory()
        session_memory.add_message("user", "Hello")
        assert session_memory.get_message_count() == 1
        print("✅ SessionMemory working")
        
        # Session manager
        session_manager = SessionManager()
        count = session_manager.get_session_count()
        print(f"✅ SessionManager working ({count} saved sessions)")
        
        # User summary
        user_summary = UserSummary()
        summary = user_summary.load()
        print(f"✅ UserSummary working ({len(summary)} chars)")
        
        # Vector DB
        vector_db = VectorDB()
        doc_count = vector_db.get_document_count()
        print(f"✅ VectorDB working ({doc_count} documents)")
        
        return True
    
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        return False


def test_tools():
    """Test tool registry."""
    print("\n" + "=" * 70)
    print("TEST 8: Tools")
    print("=" * 70)
    
    try:
        from src.tools.base import ToolRegistry
        from src.tools.save_info import SaveInfoTool
        from src.tools.file_writer import FileWriterTool
        
        registry = ToolRegistry()
        registry.register(SaveInfoTool())
        registry.register(FileWriterTool())
        
        tools = registry.list_tools()
        print(f"✅ ToolRegistry working ({len(tools)} tools registered)")
        
        return True
    
    except Exception as e:
        print(f"❌ Tools test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("           VOICE ASSISTANT INTEGRATION TEST")
    print("=" * 70)
    
    tests = [
        test_imports,
        test_config,
        test_audio,
        test_stt,
        test_tts,
        test_llm,
        test_memory,
        test_tools
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! You're ready to run: python main.py")
    else:
        print("\n⚠️  Some tests failed. Fix errors before running main.py")
    
    print("=" * 70)


if __name__ == "__main__":
    main()