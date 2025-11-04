import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PROJECT PATHS
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))
INFO_INSERTS_DIR = Path(os.getenv("INFO_INSERTS_DIR", "./data/info_inserts"))
GOOGLE_TOKENS_DIR = Path(os.getenv("GOOGLE_TOKENS_DIR", "./data/google_tokens"))

# Create directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR, INFO_INSERTS_DIR, GOOGLE_TOKENS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API KEYS
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
BING_SEARCH_API_KEY = os.getenv("BING_SEARCH_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# OPENAI SETTINGS
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# AUDIO SETTINGS
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", "3"))

# STT SETTINGS (faster-whisper)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


# PIPER TTS SETTINGS (Coqui)
PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")
PIPER_MODEL_QUALITY = os.getenv("PIPER_MODEL_QUALITY", "medium")

# VECTOR DATABASE SETTINGS
CHROMA_PERSIST_DIR = DATA_DIR / "chroma"
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDING_CHUNK_SIZE = int(os.getenv("EMBEDDING_CHUNK_SIZE", "500"))
EMBEDDING_CHUNK_OVERLAP = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", "50"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# MEMORY SETTINGS
USER_SUMMARY_FILE = DATA_DIR / "user_summary.txt"
SESSION_MEMORY_MAX_TOKENS = int(os.getenv("SESSION_MEMORY_MAX_TOKENS", "4000"))

# APPLICATION SETTINGS
APP_NAME = os.getenv("APP_NAME", "VoiceAssistant")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# VALIDATION
def validate_config():
    """
    Validate critical configuration values.
    Raises ValueError if required settings are missing in non-demo mode.
    """
    if DEMO_MODE:
        print("⚠️  Running in DEMO MODE - using stubbed responses (no API calls)")
        return
    
    errors = []
    
    # Check OpenAI API key
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-proj-xxx"):
        errors.append("OPENAI_API_KEY is missing or invalid. Get one from https://platform.openai.com/api-keys")
    
    # Check at least one search API key
    if not SERP_API_KEY and not BING_SEARCH_API_KEY:
        errors.append("No web search API key found. Set SERP_API_KEY or BING_SEARCH_API_KEY in .env")
    
    # Warn about Google API (not critical for basic operation)
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("⚠️  Google API credentials not found. Gmail/Calendar tools will be disabled.")
        print("   Run 'python scripts/setup_google_oauth.py' to set up later.")
    
    if errors:
        error_msg = "\n❌ Configuration errors:\n" + "\n".join(f"  - {err}" for err in errors)
        error_msg += "\n\n💡 Copy .env.example to .env and fill in your API keys."
        raise ValueError(error_msg)
    
    print(f"✅ Configuration loaded successfully")
    print(f"   Model: {OPENAI_MODEL}")
    print(f"   Whisper: {WHISPER_MODEL_SIZE} on {WHISPER_DEVICE}")


# HELPER FUNCTIONS
def get_whisper_device():
    """
    Determine the actual device to use for Whisper based on config and availability.
    Returns: "cuda", "cpu"
    """
    if WHISPER_DEVICE == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"
    return WHISPER_DEVICE


# Run validation when module is imported (unless in test mode)
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        if not DEMO_MODE:
            print(str(e))
            print("\n🚀 To test without API keys, set DEMO_MODE=true in .env")


# config test
if __name__ == "__main__":
    """Test configuration loading"""

    try:
        validate_config()
        print("✅ All critical configurations validated")
    except ValueError as e:
        print(f"\n❌ Validation failed:\n{e}")