# 🚀 Voice AI Assistant - Setup Guide

## 📋 Prerequisites

- **Python 3.10+** (3.11 recommended)
- **4GB RAM minimum** (8GB recommended)
- **Microphone + Speakers**
- **Internet connection** (for API calls)

---

## 🔧 Installation Steps

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd voice-ai-assistant
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys
notepad .env  # Windows
nano .env     # Linux/Mac
```

**Required API Keys:**
```bash
# OpenAI (REQUIRED)
OPENAI_API_KEY=sk-proj-your_key_here

# SerpAPI (REQUIRED for web search)
SERP_API_KEY=your_serpapi_key_here
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- SerpAPI: https://serpapi.com/ (100 free searches/month)

---

## ✅ Verify Setup

Run the integration test:
```bash
python tests/test_integration.py
```

**Expected output:**
```
✅ All tests passed! You're ready to run: python main.py
```

If any tests fail, check:
1. API keys are correct in `.env`
2. All dependencies installed
3. Microphone/speakers connected
4. Internet connection active

---

## 🎤 Launch Application

```bash
python main.py
```

---

## 📖 User Guide

### First Time Launch

1. **Startup Menu** appears:
   ```
   📚 No saved sessions yet.
   
   Options:
   • Press ENTER to start new session
   • Type 'stats' for usage statistics
   • Type 'exit' to quit
   ```

2. **Select Recording Mode**:
   ```
   [1] Press-to-Speak (5 seconds)
   [2] Voice Activity Detection (hands-free)
   ```

3. **Start Talking!**
   - Press-to-speak: Press ENTER, speak for 5 seconds
   - VAD: Just speak naturally, it detects automatically

---

### Voice Commands

**Session Management:**
- `"save session"` → Save conversation (prompts for name)
- `"load session"` → Show session list and load
- `"list sessions"` → Display all saved sessions
- `"clear conversation"` → Reset current chat

**TTS Speed:**
- `"speak slower"` → Reduce speed to 0.75x
- `"speak faster"` → Increase speed to 1.25x
- `"speak normal"` → Reset to 1.0x

**Exit:**
- `"exit"` / `"quit"` / `"goodbye"` → End conversation

---

### Tool Usage Examples

**Web Search:**
```
You: What's the weather in Cairo today?
AI: [searches web] The weather is sunny, 28°C...
```

**Search Documents:**
```
You: What did I upload about the project?
AI: [searches RAG] According to your documents...
```

**Save Notes:**
```
You: Remember I have a meeting tomorrow at 2 PM
AI: [saves to notes] Got it! Saved to your notes.
```

**Draft Email:**
```
You: Draft email to john@example.com about meeting
AI: [creates Gmail draft] Email draft created in Gmail.
```

**Export Content:**
```
You: Save this conversation summary to a file
AI: [writes file] Created file: summary.txt
```

---

## 🔧 Optional Setup

### Gmail Integration (Optional)

To enable Gmail drafts:

1. **Run setup wizard:**
   ```bash
   python src/scripts/setup_google_oauth.py
   ```

2. **Follow instructions:**
   - Creates Google Cloud project
   - Enables Gmail API
   - Downloads OAuth credentials
   - Authorizes application

3. **Test:**
   ```
   You: Draft email to test@example.com
   ```

---

### Upload Documents (Optional)

To use RAG (document search):

1. **Upload PDFs/text files:**
   ```bash
   python src/scripts/ingest_documents.py --file document.pdf
   ```

2. **Or upload entire folder:**
   ```bash
   python src/scripts/ingest_documents.py --directory ./documents/
   ```

3. **Test:**
   ```
   You: What does my document say about X?
   ```

---

## 📊 Usage Statistics

View your usage at any time:

**From Startup Menu:**
```
Choice: stats
```

**Shows:**
- Total sessions, messages, duration
- API costs (OpenAI tokens)
- Most used tools
- Performance metrics

---

## 🐛 Troubleshooting

### "Microphone not detected"
- Check microphone is connected
- Run: `python -m sounddevice`
- Select correct input device

### "OpenAI API error"
- Verify API key in `.env`
- Check account has credits: https://platform.openai.com/usage
- Try different model (gpt-3.5-turbo cheaper)

### "Whisper model download stuck"
- First run downloads ~140MB model
- Check internet connection
- Try different model: `WHISPER_MODEL_SIZE=tiny` in `.env`

### "TTS audio garbled"
- Check speaker volume
- Try different voice: `PIPER_VOICE=en_US-amy-medium` in `.env`

### "VAD not detecting speech"
- Adjust aggressiveness: `VAD_AGGRESSIVENESS=2` in `.env`
- Speak louder/closer to mic
- Use press-to-speak mode instead

---

## 🎯 Tips for Best Experience

### Press-to-Speak Mode
✅ Best for:
- Noisy environments
- Precise commands
- Quick queries

💡 Tips:
- Speak immediately after pressing ENTER
- Keep responses under 5 seconds
- Speak clearly and at normal pace

### VAD Mode
✅ Best for:
- Hands-free operation
- Natural conversation
- Long responses

💡 Tips:
- Pause 1 second before speaking
- Speak naturally (don't rush)
- Clear silence = end of turn (300ms)

---

## 🔐 Privacy & Security

**Local Data:**
- User summary: `./data/user_summary.txt`
- Sessions: `./data/sessions.db` (SQLite)
- Notes: `./data/user_notes.txt`
- Analytics: `./data/analytics.jsonl`

**API Calls:**
- OpenAI: Transcription + chat (encrypted HTTPS)
- SerpAPI: Web search (encrypted HTTPS)
- Google: Gmail drafts only (OAuth2)

**No Data Sharing:**
- All data stored locally
- No telemetry sent to developers
- API providers have own privacy policies

---

## 💰 Cost Estimates

**OpenAI API** (gpt-4-turbo):
- Average conversation (10 turns): ~2,000 tokens = $0.08
- One hour session: ~$0.50
- Monthly (daily use): ~$15

**SerpAPI:**
- Free tier: 100 searches/month
- Paid: $50/month for 5,000 searches

**Gmail API:**
- Free (no quotas for draft creation)

**Total monthly (heavy use):** ~$20-30

💡 **Cost Savings:**
- Use `gpt-3.5-turbo` (10x cheaper)
- Enable rate limiting
- Monitor with `stats` command

---

## 📝 Configuration Options

Edit `.env` to customize:

```bash
# Model Selection
OPENAI_MODEL=gpt-4o  # or gpt-3.5-turbo
WHISPER_MODEL_SIZE=base            # tiny/small/medium/large
PIPER_VOICE=en_US-lessac-medium    # see Piper docs

# Audio Settings
AUDIO_SAMPLE_RATE=16000
VAD_AGGRESSIVENESS=3               # 0-3 (3=most aggressive)

# Memory
SESSION_MEMORY_MAX_TOKENS=4000
RAG_TOP_K=5

# Debug
DEBUG_MODE=false
```

---

## 🆘 Support

**Check Logs:**
```bash
# View latest log
cat logs/*.log | tail -100
```

**Common Issues:**
1. Config validation fails → Check `.env` file
2. API errors → Verify API keys and credits
3. Audio issues → Test with `python -m sounddevice`
4. Model loading slow → Normal on first run (downloads models)

---

## 🎓 Next Steps

1. ✅ Complete setup and run tests
2. ✅ Try both recording modes
3. ✅ Test voice commands
4. ✅ Upload documents for RAG
5. ✅ Set up Gmail integration
6. ✅ Review usage stats

**Ready to build your portfolio?**
- Add custom tools
- Integrate more APIs
- Improve prompts
- Extend memory system

---

## 📚 Documentation

- **Architecture:** See `/docs/ARCHITECTURE.md`
- **API Reference:** See `/docs/API.md`
- **Contributing:** See `/docs/CONTRIBUTING.md`

---

**🎤 Enjoy your voice assistant!**