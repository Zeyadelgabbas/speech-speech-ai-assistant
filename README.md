# Voice Assistant - Production-Grade Speech-to-Speech AI

A privacy-conscious, locally-running voice assistant with OpenAI brain, local STT/TTS, RAG capabilities, and Google API integrations.

---

## 🎯 Features

- **Local Speech Processing**: faster-whisper (STT) + Piper TTS (ultra-fast, low resource)
- **OpenAI GPT-4 Brain**: Function calling for tool execution
- **Three-Layer Memory**:
  - User summary (text file, manual updates via voice)
  - Session chat memory (in-memory, cleared each session)
  - Vector database (ChromaDB + OpenAI embeddings for RAG)
- **Voice Commands**:
  - `"write info [content]"` - Save info directly to vector DB
  - `"update my summary"` - Append session insights to user profile
  - Normal queries trigger LLM + tools
- **Tools**:
  - Web search (SerpAPI/Bing)
  - RAG query (search uploaded PDFs/notes)
  - Gmail (draft composition)
  - Google Calendar (read events)
  - File writer (local file operations)
- **CLI Modes**: Press-to-talk, continuous listening, demo mode (no API keys)

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Operating System**: Windows 10/11, macOS, or Linux
- **Optional**: NVIDIA GPU with CUDA 11.x/12.x for faster STT

### 2. Installation

**Windows (PowerShell):**
```powershell
# Clone or download the project
cd voice-assistant

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**macOS/Linux (bash):**
```bash
# Clone or download the project
cd voice-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# Required: OPENAI_API_KEY, SERP_API_KEY (or BING_SEARCH_API_KEY)
# Optional: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (for Gmail/Calendar)
```

**Get API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **SerpAPI**: https://serpapi.com/manage-api-key (100 free searches/month)
- **Google OAuth**: Run `python scripts/setup_google_oauth.py` after setup

### 4. Test Configuration
```bash
python config.py
```

You should see:
```
✅ Configuration loaded successfully
   Model: gpt-4-turbo-preview
   Whisper: base on auto
   TTS: en_US-lessac-medium
```

### 5. Run the Assistant

**Press-to-Talk Mode** (recommended for testing):
```bash
python main.py --mode press
```
Press `Enter` to record, speak, then press `Enter` again to stop.

**Continuous Mode** (hands-free with voice detection):
```bash
python main.py --mode continuous
```

**Demo Mode** (no API keys, uses stubs):
```bash
python main.py --demo
```

---

## 📚 Document Ingestion

Upload PDFs or text files to the vector database:
```bash
# Ingest a PDF
python scripts/ingest_documents.py --file ./my_notes.pdf

# Ingest a text file
python scripts/ingest_documents.py --file ./research.txt

# Ingest a directory (all PDFs/TXT)
python scripts/ingest_documents.py --directory ./documents/
```

---

## 🗣️ Voice Commands

| Command | Action | Example |
|---------|--------|---------|
| Normal query | LLM decides which tools to use | "What's on my calendar tomorrow?" |
| `"write info [content]"` | Save directly to vector DB (bypasses LLM) | "write info Meeting notes from today..." |
| `"update my summary"` | Summarize session and append to profile | "update my summary" |
| Web search | LLM calls web search tool | "Search for latest AI news" |
| RAG query | LLM queries vector DB | "What did I upload about project X?" |
| Gmail | Compose draft (requires OAuth) | "Draft email to John about meeting" |
| Calendar | Read events (requires OAuth) | "What's my schedule this week?" |

---

## 🔧 Configuration Options

### Whisper (STT) Models

Edit `.env` to change `WHISPER_MODEL_SIZE`:

| Model | Size | Speed (CPU) | Accuracy | Use Case |
|-------|------|-------------|----------|----------|
| `tiny` | 39M | Very fast | Good | Testing |
| `base` | 74M | Fast | Better | **Recommended** |
| `small` | 244M | Medium | Good | Balanced |
| `medium` | 769M | Slow | Very good | High accuracy |
| `large-v3` | 1550M | Very slow | Best | GPU only |

### Piper TTS Voices

Edit `.env` to change `PIPER_VOICE`:

| Voice | Quality | Speed | Style |
|-------|---------|-------|-------|
| `en_US-lessac-medium` | High | Fast | **Default, neutral** |
| `en_US-amy-medium` | High | Fast | Friendly |
| `en_GB-alan-medium` | High | Fast | British accent |

Full list: https://rhasspy.github.io/piper-samples/

### OpenAI Models

Edit `.env` to change `OPENAI_MODEL`:

| Model | Cost (per 1M tokens) | Speed | Quality |
|-------|---------------------|-------|---------|
| `gpt-3.5-turbo` | $0.50 / $1.50 | Fast | Good |
| `gpt-4-turbo-preview` | $10 / $30 | Medium | **Best** |
| `gpt-4o` | $5 / $15 | Fast | Excellent |

---

## 🧪 Testing

Run unit tests:
```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_stt.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 📁 Project Structure
```
voice-assistant/
├── config.py                    # Central configuration
├── main.py                      # CLI entrypoint
├── requirements.txt             # Dependencies
├── .env                         # API keys (create from .env.example)
│
├── src/
│   ├── audio/                   # Recording, playback, VAD
│   ├── stt/                     # Speech-to-text (faster-whisper)
│   ├── tts/                     # Text-to-speech (Piper)
│   ├── llm/                     # OpenAI client + prompts
│   ├── memory/                  # User summary, session memory, vector DB
│   ├── tools/                   # Web search, RAG, Gmail, Calendar, file writer
│   ├── assistant/               # Command router, session manager
│   └── utils/                   # Logger, demo stubs, helpers
│
├── scripts/
│   ├── ingest_documents.py      # PDF/TXT ingestion
│   └── setup_google_oauth.py    # Google API setup wizard
│
├── tests/                       # Unit and integration tests
├── data/                        # Local data storage (gitignored)
│   ├── chroma/                  # Vector database
│   ├── user_summary.txt         # User profile
│   ├── info_inserts/            # "write info" outputs
│   └── google_tokens/           # OAuth tokens
└── logs/                        # Timestamped log files
```

---

## 🔒 Privacy & Security

**What stays local:**
- All audio (never uploaded)
- STT transcription (faster-whisper on your machine)
- TTS synthesis (Piper on your machine)
- Vector database (ChromaDB, stored locally)
- User summary file

**What goes to cloud:**
- Transcribed **text** to OpenAI API (not audio)
- Search queries to SerpAPI/Bing
- OAuth tokens for Gmail/Calendar (stored locally)

**Cost control:**
- Set spending limits in OpenAI dashboard
- Use `gpt-3.5-turbo` for 10x lower cost
- Demo mode for testing without API calls

**Never commit:**
- `.env` (API keys)
- `data/google_tokens/` (OAuth tokens)
- `data/` directory (personal data)

---

## 🐛 Troubleshooting

### "OPENAI_API_KEY is missing"
Copy `.env.example` to `.env` and add your API key from https://platform.openai.com/api-keys

### "No web search API key found"
Add `SERP_API_KEY` or `BING_SEARCH_API_KEY` to `.env`, or set `DEMO_MODE=true` to test without keys.

### Slow transcription (STT)
- Use a smaller Whisper model: `WHISPER_MODEL_SIZE=tiny`
- Enable GPU: Ensure CUDA is installed, set `WHISPER_DEVICE=cuda`

### Slow TTS
Piper is already optimized for CPU. If still slow:
- Use a smaller voice: `PIPER_VOICE=en_US-lessac-low`

### Google API errors
Run `python scripts/setup_google_oauth.py` to complete OAuth flow.

### "Module not found" errors
Ensure virtual environment is activated:
- Windows: `.\venv\Scripts\Activate.ps1`
- macOS/Linux: `source venv/bin/activate`

---

## 📝 Logs

All debug logs are written to `./logs/YYYY-MM-DD_HH-MM-SS.log`. Console output is kept minimal (only user-facing messages).

To view logs:
```bash
# Windows
type logs\2025-11-03_14-30-45.log

# macOS/Linux
tail -f logs/2025-11-03_14-30-45.log
```

---

## 🎓 Learning Resources

- **OpenAI Function Calling**: https://platform.openai.com/docs/guides/function-calling
- **faster-whisper**: https://github.com/guillaumekln/faster-whisper
- **Piper TTS**: https://github.com/rhasspy/piper
- **ChromaDB**: https://docs.trychroma.com/
- **Google APIs**: https://developers.google.com/calendar/api/quickstart/python

---

## 📄 License

MIT License - feel free to modify and use for your projects.

---

## 🙋 Support

- Check logs in `./logs/` for detailed error messages
- Run tests: `pytest tests/ -v`
- Enable demo mode: `DEMO_MODE=true` in `.env`

---

**Built with ❤️ for learning AI engineering**