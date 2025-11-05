# test_voice_pipeline.py (create this to test)

from src.audio.recorder import AudioRecorder
from src.audio.player import AudioPlayer
from src.stt.faster_whisper import FasterWhisperSTT
from src.tts.piper_tts import PiperTTS
from src.llm.openai_client import OpenAIClient
from src.llm.prompts import get_system_prompt

# Initialize
recorder = AudioRecorder()
player = AudioPlayer(sample_rate=22050)
stt = FasterWhisperSTT()
tts = PiperTTS()
llm = OpenAIClient()

# System prompt
messages = [{"role": "system", "content": get_system_prompt()}]

print("🎤 Press Enter to speak...")
input()

# Record
audio = recorder.record_fixed_duration(5.0)
print("🔄 Transcribing...")

# STT
result = stt.transcribe(audio)
user_text = result["text"]
print(f"You: {user_text}")

# LLM
messages.append({"role": "user", "content": user_text})
response = llm.chat(messages)
assistant_text = response["content"]
print(f"Assistant: {assistant_text}")

# TTS
print("🔊 Generating speech...")
audio_response = tts.synthesize(assistant_text)

# Play
player.play(audio_response)
print("✅ Done!")