# 🎤 Speech-to-Speech AI Voice Assistant

> **An intelligent, privacy-focused voice assistant with conversational memory, tool execution, and real-time speech interaction**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success)](https://github.com/Zeyadelgabbas/speech-speech-ai-assistant)

---

## 🌟 Overview

A production-ready voice assistant that combines **Speech-to-Text (STT)**, **Large Language Models (LLMs)**, and **Text-to-Speech (TTS)** into a seamless conversational experience. Built with local processing capabilities and intelligent function calling, it offers session-based memory, document search (RAG), web search, Gmail integration, and real-time voice activity detection.

**Perfect for:** Portfolio projects, AI engineering demonstrations, and understanding end-to-end voice AI systems.

---

## ✨ Key Features

### 🎙️ **Dual Recording Modes**
- **Press-to-Speak**: Fixed 5-second recording for precise control
- **Voice Activity Detection (VAD)**: Hands-free operation with automatic speech detection using **WebRTC VAD**

### 🧠 **Intelligent Conversation**
- **LLM-Powered**: Uses OpenAI GPT-4 with function calling for natural responses
- **Session Memory**: Persistent conversation history with SQLite storage
- **User Profiling**: Long-term preference learning and personalization

### 🔧 **5 Production Tools**
| Tool | Description | Integration |
|------|-------------|-------------|
| 🌐 **Web Search** | Real-time Google search | SerpAPI |
| 📚 **RAG Query** | Document Q&A system | ChromaDB + OpenAI Embeddings |
| ✉️ **Gmail Drafts** | Email composition (no auto-send) | Google Gmail API (OAuth2) |
| 📝 **Notes Manager** | Quick note storage/retrieval | Local file system |
| 💾 **File Writer** | Export conversations/summaries | Text file export |

### 📊 **Analytics & Monitoring**
- Real-time cost tracking (tokens, API calls)
- Usage statistics dashboard
- Tool execution frequency
- Session duration & error rates

---

## 🎬 User Experience

### **Startup**
```
🎤 VOICE AI ASSISTANT v1.0

📚 Saved Sessions:
   [1] meeting notes (10 messages, 2025-11-12)
   [2] project planning (15 messages, 2025-11-11)

Options:
  • Type 1-2 to load session
  • Press ENTER for new session
  • Type 'stats' for analytics

Choice: _
```

### **Conversation Flow**
```
🧑 User: What's the weather in Cairo today?

🤖 Thinking...
   🔧 [web_search]...

🤖 Assistant: The weather in Cairo is sunny with 28°C...
🔊 Speaking...

⏺️  Ready to listen...
```

### **Voice Commands**
- `"save session"` → Save with custom name
- `"load session"` → Resume previous conversation
- `"draft email to john@example.com"` → Create Gmail draft
- `"search my documents for budget"` → Query RAG database
- `"speak slower"` → Adjust TTS speed

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Voice Assistant                    │
├─────────────────────────────────────────────────────┤
│  Audio Input → STT → LLM + Tools → TTS → Audio Out │
└─────────────────────────────────────────────────────┘

Pipeline:
1. Record Audio (Press-to-Speak or VAD)
2. Transcribe (Faster Whisper)
3. Route Commands / Call LLM (GPT-4 + Function Calling)
4. Execute Tools (Web/RAG/Gmail/Notes/Files)
5. Synthesize Speech (Piper TTS)
6. Play Audio (Speakers)
7. Log Analytics
```

### **Tech Stack**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **STT** | Faster Whisper (`base` model) | High-accuracy speech recognition (16kHz) |
| **LLM** | OpenAI GPT-4 Turbo | Natural language understanding + tool orchestration |
| **TTS** | Piper TTS (ONNX) | Natural speech synthesis (22kHz) |
| **VAD** | WebRTC VAD (Level 3) | Real-time silence detection |
| **Vector DB** | ChromaDB | Document embeddings for RAG |
| **Embeddings** | OpenAI `text-embedding-3-small` | 1536-dim semantic search |
| **Web Search** | SerpAPI | Real-time Google search results |
| **Email** | Google Gmail API (OAuth2) | Draft creation (no auto-send) |
| **Memory** | SQLite + JSON | Session persistence + analytics |
| **Tools** | LangChain-style function calling | Dynamic tool selection |

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.10+
- Microphone + Speakers
- OpenAI API key
- SerpAPI key (optional: 100 free searches/month)

### **Installation**
```bash
# Clone repository
git clone https://github.com/Zeyadelgabbas/speech-speech-ai-assistant.git
cd speech-speech-ai-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

### **Run**
```bash
# Test setup
python tests/test_integration.py

# Launch assistant
python main.py
```

---

## 📋 Configuration

Edit `.env`:
```bash
# Required
OPENAI_API_KEY=sk-proj-your_key_here
SERP_API_KEY=your_serpapi_key_here

# Optional
WHISPER_MODEL_SIZE=base  # tiny/small/medium/large
PIPER_VOICE=en_US-lessac-medium
VAD_AGGRESSIVENESS=3  # 0-3 (3=most sensitive)
```

---

## 🔧 Features Breakdown

### **1. Retrieval-Augmented Generation (RAG)**
- Upload PDFs/text files: `python src/scripts/ingest_documents.py --file doc.pdf`
- Query with voice: `"What does my document say about budget?"`
- Semantic search with ChromaDB + OpenAI embeddings

### **2. Gmail Integration**
- OAuth2 setup: `python src/scripts/setup_google_oauth.py`
- Voice command: `"Draft email to boss about project update"`
- Creates draft in Gmail (user reviews before sending)

### **3. Session Management**
- Auto-save conversations with custom names
- Load previous sessions with full context
- SQLite persistence with conversation history

### **4. Smart Tool Selection**
- Context-aware tool activation (reduces token usage)
- Always available: Notes, File Writer
- Conditional: Web Search, RAG, Gmail (triggered by keywords)

---

## 📊 Analytics Dashboard

View comprehensive statistics:
```bash
Choice: stats
```

**Metrics tracked:**
- Total sessions, messages, tokens (prompt + completion)
- Estimated API costs
- Tool execution frequency
- Average session duration & messages per session
- Error rates and performance metrics

---

## 🎯 Use Cases

- **Personal Assistant**: Schedule management, note-taking, reminders
- **Document Q&A**: Query your PDFs and documents with natural language
- **Email Drafting**: Compose emails hands-free with Gmail integration
- **Research Tool**: Web search integration for real-time information
- **Learning & Development**: Portfolio project demonstrating AI engineering skills

---

## 🛠️ Development

### **Project Structure**
```
speech-speech-ai-assistant/
├── main.py                      # Entry point
├── src/
│   ├── assistant/              # Core orchestration
│   ├── audio/                  # Recording, playback, VAD
│   ├── stt/                    # Faster Whisper integration
│   ├── tts/                    # Piper TTS
│   ├── llm/                    # OpenAI client + prompts
│   ├── memory/                 # Session, user, vector DB
│   ├── tools/                  # Function calling tools
│   └── utils/                  # Config, logging
├── data/                       # User data (gitignored)
└── tests/                      # Integration tests
```

### **Adding New Tools**
1. Create tool class inheriting from `BaseTool`
2. Implement `name`, `description`, `parameters_schema`, `execute()`
3. Register in `VoiceAssistant._register_tools()`

---

## 🐛 Troubleshooting

**Microphone Issues:**
```bash
python -m sounddevice  # List audio devices
```

**API Errors:**
- Verify API keys in `.env`
- Check OpenAI account credits

**VAD Not Detecting Speech:**
- Adjust `VAD_AGGRESSIVENESS` (0-3)
- Use Press-to-Speak mode instead

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file

---

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

---

## 👤 Author

**Zeyad Emad**
- GitHub: [@Zeyadelgabbas](https://github.com/Zeyadelgabbas)
- LinkedIn: [Zeyad Elgabas](https://www.linkedin.com/in/zeyad-elgabas-9862082b7)
- Email: Zeyadelgabas@gmail.com

---

## 🌟 Acknowledgments

Built with:
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [Piper TTS](https://github.com/rhasspy/piper)
- [OpenAI API](https://platform.openai.com/) 
- [ChromaDB](https://www.trychroma.com/)
- [LangChain](https://www.langchain.com/)

---

**⭐ If you find this project useful, please star the repository!**