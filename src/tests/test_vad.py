import sounddevice as sd
import numpy as np
from src.audio import VoiceActivityDetector

print("Testing VAD with aggressiveness levels...")

# Record 5 seconds
audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='float32')
print("Speak for 5 seconds...")
sd.wait()
audio = audio.flatten()

# Test with different aggressiveness levels
for agg in [1, 2, 3]:
    vad = VoiceActivityDetector(aggressiveness=agg)
    
    # Split into 30ms frames
    frame_size = int(16000 * 0.03)  # 480 samples
    num_frames = len(audio) // frame_size
    
    speech_frames = 0
    for i in range(num_frames):
        start = i * frame_size
        end = start + frame_size
        frame = audio[start:end]
        
        if vad.is_speech(frame):
            speech_frames += 1
    
    percentage = (speech_frames / num_frames) * 100
    print(f"Aggressiveness {agg}: {speech_frames}/{num_frames} frames detected as speech ({percentage:.1f}%)")