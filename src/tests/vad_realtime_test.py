import sounddevice as sd
import numpy as np
from src.audio import VoiceActivityDetector

print("="*70)
print("🎤 FIXED VAD REAL-TIME TEST")
print("="*70)

sample_rate = 16000
frame_duration_ms = 30   # VALID for WebRTC VAD!
frame_size = int(sample_rate * frame_duration_ms / 1000)

print(f"Frame size: {frame_size} samples")

# Initialize VAD
vad = VoiceActivityDetector(
    sample_rate=sample_rate,
    aggressiveness=2,
    frame_duration_ms=frame_duration_ms,
    speech_trigger_frames=3
)

print("\n🎤 Speak for 5 seconds!")

num_frames = int(5 / (frame_duration_ms / 1000))

for i in range(num_frames):
    audio_frame = sd.rec(
        frame_size,
        samplerate=sample_rate,
        channels=1,      # MONO FIX
        dtype='float32'
    )
    sd.wait()

    # Debug amplitude
    print(f"[{i}] MIN={audio_frame.min():.5f} MAX={audio_frame.max():.5f}")

    # Flatten
    audio_frame = audio_frame.flatten()

    # Normalize weak microphones
    max_amp = np.abs(audio_frame).max()
    if max_amp < 0.01:  
        audio_frame = audio_frame / (max_amp + 1e-6)

    # Process with VAD
    started, ended = vad.process_frame(audio_frame)

    if started:
        print(f"   🎤 Speech STARTED at {i}")

    if ended:
        print(f"   🎤 Speech ENDED at {i}")
