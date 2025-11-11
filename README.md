# 🎤 Voice AI Assistant

**A production-ready, multi-modal AI assistant powered by GPT-4, Whisper, and Piper TTS**

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Features](#-features) • [Quick Start](#-quick-start) • [Demo](#-demo) • [Architecture](#-architecture) • [Tech Stack](#-tech-stack)

</div>

---

## 🎯 What is This?

A **fully functional voice-controlled AI assistant** that you can talk to naturally. It understands speech, searches the web, remembers conversations, and can help with tasks like drafting emails and managing notes.

**Built for learning and showcasing modern AI integration.**

---

## ✨ Features

### 🗣️ **Natural Voice Interaction**
- **Press-to-Speak**: Record for 5 seconds with a keypress
- **Voice Activity Detection (VAD)**: Hands-free mode that detects when you start/stop speaking
- **Natural TTS**: High-quality speech synthesis (adjustable speed)

### 🧠 **Intelligent AI Brain**
- **GPT-4 Integration**: Context-aware responses with function calling
- **RAG (Retrieval-Augmented Generation)**: Search your uploaded PDFs and documents
- **Memory System**: Remembers user preferences across sessions

### 🛠️ **Powerful Tools**
- 🔍 **Web Search**: Real-time Google search integration
- 📄 **Document Search**: Query your personal knowledge base
- ✉️ **Gmail Drafts**: Create email drafts (OAuth-secured)
- 📝 **File Export**: Save content to organized files
- 💾 **Notes Manager**: Quick information storage and retrieval

### 💬 **Smart Commands**
Voice commands that work instantly (no API calls):
- `"save session [name]"` - Save conversation with auto-summary
- `"load session [name]"` - Resume previous conversations
- `"speak slower/faster"` - Adjust speech speed
- `"list sessions"` - View saved conversations

---

## 🚀 Quick Start

### **1. Prerequisites**
```bash
# Python 3.10 or higher
python --version

# Microphone and speakers
# Internet connection (for API calls)
```

### **2. Installation**
```bash
# Clone repository
git clone https://github.com/yourusername/voice-ai-assistant.git
cd voice-ai-assistant

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env and add your API keys (see below)
```

### **3. Get API Keys**
1. **OpenAI API Key** (Required)
   - Sign up at [platform.openai.com](https://platform.openai.com/)
   - Create API key → Add to `.env` as `OPENAI_API_KEY`

2. **SerpAPI Key** (Optional - for web search)
   - Sign up at [serpapi.com](https://serpapi.com/)
   - Get free API key → Add to `.env` as `SERP_API_KEY`

3. **Gmail OAuth** (Optional - for email drafts)
   - Run: `python src/scripts/setup_google_oauth.py`
   - Follow browser authorization flow

### **4. Run**
```bash
# Start the assistant
python main.py

# Choose mode:
# [1] Press-to-Speak (5 seconds)
# [2] Voice Activity Detection (hands-free)
```

---

## 🎬 Demo

```
════════════════════════════════════════════════════════════════════
                    🎤 VOICE AI ASSISTANT
════════════════════════════════════════════════════════════════════

🎤 Listening... [████████████████████] 3s

🧑 User: What's the weather in Cairo today?

🤖 Assistant: Let me check that for you...
   🔧 [web_search: weather Cairo Egypt today]

🤖 Assistant: The weather in Cairo is currently sunny with a 
   temperature of 28°C. Expect clear skies throughout the day.

🔊 Speaking... ✅

════════════════════════════════════════════════════════════════════
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Voice Assistant                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🎤 Audio Input  →  🧠 Whisper STT  →  🤖 GPT-4 + Tools   │
│                                              ↓              │
│  🔊 Audio Output ←  🗣️ Piper TTS   ←  📝 Response         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Memory: Session (SQLite) + Vector DB (ChromaDB)           │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **STT**: Faster-Whisper (local, privacy-focused)
- **LLM**: OpenAI GPT-4 with function calling
- **TTS**: Piper (high-quality, open-source)
- **Vector DB**: ChromaDB for document embeddings
- **Tools**: 5 production-ready integrations

---

## 📊 Project Structure

```
voice-ai-assistant/
├── main.py                      # Entry point
├── src/
│   ├── audio/                   # Recording & playback
│   ├── stt/                     # Speech-to-text (Whisper)
│   ├── tts/                     # Text-to-speech (Piper)
│   ├── llm/                     # LLM client & prompts
│   ├── memory/                  # Session & vector storage
│   ├── tools/                   # Function calling tools
│   ├── assistant/               # Core orchestration
│   └── utils/                   # Config & logging
├── data/                        # User data (gitignored)
├── logs/                        # Application logs
└── tests/                       # Unit tests
```

---

## 🛠️ Tech Stack

| Component | Technology | Why? |
|-----------|-----------|------|
| **STT** | Faster-Whisper | Local processing, high accuracy |
| **LLM** | OpenAI GPT-4 | Best-in-class reasoning + tools |
| **TTS** | Piper | Natural voice, open-source |
| **Vector DB** | ChromaDB | Fast semantic search |
| **Embeddings** | OpenAI text-embedding-3 | High-quality, cost-effective |
| **Web Search** | SerpAPI | Reliable Google search API |
| **Audio I/O** | sounddevice | Cross-platform audio |
| **VAD** | WebRTC VAD | Production-grade detection |

---

## 📚 Usage Examples

### **Basic Conversation**
```
You: "Tell me a joke"
AI: "Why did the developer quit their job? They didn't get arrays!"
```

### **Web Search**
```
You: "What are the latest AI news?"
AI: [Searches web, summarizes top 3 results]
```

### **Document Search**
```bash
# First, upload documents:
python src/scripts/ingest_documents.py --file notes.pdf

# Then ask:
You: "What did I upload about project deadlines?"
AI: [Searches your documents, provides relevant info]
```

### **Session Management**
```
You: "Save session as project planning"
AI: ✅ Session saved and summary updated!

You: "Load session project planning"
AI: ✅ Loaded 24 messages from March 15th
```

---

## ⚙️ Configuration

Key settings in `.env`:

```bash
# Required
OPENAI_API_KEY=sk-...

# Model Selection
OPENAI_MODEL=gpt-4-turbo-preview  # or gpt-3.5-turbo
WHISPER_MODEL_SIZE=base            # tiny/base/small/medium
PIPER_VOICE=en_US-lessac-medium

# Audio Settings
AUDIO_SAMPLE_RATE=16000
VAD_AGGRESSIVENESS=3               # 0-3 (3 = most aggressive)

# Memory
SESSION_MEMORY_MAX_TOKENS=4000
RAG_TOP_K=5
```

---

## 🧪 Testing

```bash
# Test individual components
python src/audio/recorder.py      # Test microphone
python src/stt/faster_whisper.py  # Test transcription
python src/tts/piper_tts.py       # Test speech synthesis

# Test tools
python src/tools/web_search.py
python src/tools/rag_query.py

# Run full test suite
python -m pytest tests/
```

---

## 🐛 Troubleshooting

### **"No audio detected"**
- Check microphone permissions
- Test with: `python src/audio/recorder.py`
- Try adjusting `VAD_AGGRESSIVENESS` (lower = more sensitive)

### **"OpenAI API error"**
- Verify API key in `.env`
- Check account has credits: [platform.openai.com/account/billing](https://platform.openai.com/account/billing)

### **"Whisper model download fails"**
- Ensure stable internet connection
- Models download to `~/.cache/huggingface/` (2-500MB depending on size)

### **"Gmail tool not working"**
- Run OAuth setup: `python src/scripts/setup_google_oauth.py`
- Ensure `credentials.json` in `data/google_tokens/`

---

## 🎓 Learning Outcomes

This project demonstrates:
- ✅ **Multi-modal AI integration** (speech, text, search)
- ✅ **Production patterns** (error handling, logging, rate limiting)
- ✅ **Clean architecture** (separation of concerns, dependency injection)
- ✅ **RAG implementation** (vector databases, embeddings)
- ✅ **Function calling** (LLM tool use, agentic behavior)
- ✅ **State management** (session persistence, memory systems)

---

## 📈 Future Enhancements

- [ ] Web UI (FastAPI + React)
- [ ] Streaming responses (real-time text generation)
- [ ] Multi-language support
- [ ] Calendar integration
- [ ] Custom wake word detection
- [ ] Mobile app (React Native)

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** - GPT-4 and Whisper models
- **Rhasspy** - Piper TTS engine
- **WebRTC** - Voice Activity Detection
- **ChromaDB** - Vector database

---

## 📬 Contact

**Your Name** - [your.email@example.com](mailto:your.email@example.com)

Project Link: [https://github.com/yourusername/voice-ai-assistant](https://github.com/yourusername/voice-ai-assistant)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ and ☕ by [Your Name]

</div>