import sounddevice as sd
import numpy as np

sample_rate = 16000

print("\n🎤 Testing microphone raw input...")
print("Speak for 1 second...\n")

audio = sd.rec(
    int(16000*0.1),                # 1 second
    samplerate=sample_rate,
    channels=1,
    dtype='float32'
)
sd.wait()

print("Raw stats:")
print("  MIN:", float(audio.min()))
print("  MAX:", float(audio.max()))
print("  MEAN:", float(audio.mean()))
