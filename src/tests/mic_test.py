"""
Test microphone input and volume levels.
Run this to diagnose VAD issues.
"""
import sounddevice as sd
import numpy as np

print("=" * 70)
print("🎤 MICROPHONE TEST")
print("=" * 70)

# List available devices
print("\n📋 Available Audio Devices:")
devices = sd.query_devices()
sd.wait()

print("DEFAULT : ",sd.default.device)
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        default = " (DEFAULT)" if i == sd.default.device[0] else ""
        print(f"   [{i}] {device['name']}{default}")
        print(f"       Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']}Hz")

print("\n" + "=" * 70)
print("🎤 Recording 3 seconds...")
print("Speak loudly and clearly: 'Hello, testing one two three'")
print("=" * 70)

# Record
audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='float32')
sd.wait()

audio = audio.flatten()
max_amp = np.abs(audio).max()
mean_amp = np.abs(audio).mean()
rms = np.sqrt(np.mean(audio**2))

print("\n📊 RESULTS:")
print("=" * 70)
print(f"   Max Amplitude:  {max_amp:.4f}")
print(f"   Mean Amplitude: {mean_amp:.4f}")
print(f"   RMS Level:      {rms:.4f}")
print("=" * 70)

# Analysis
print("\n🔍 ANALYSIS:")
if max_amp < 0.001:
    print("   ❌ MICROPHONE NOT WORKING")
    print("\n   Possible causes:")
    print("   1. Microphone is muted or unplugged")
    print("   2. Wrong device selected")
    print("   3. Microphone permissions disabled")
    print("\n   Solutions:")
    print("   1. Check system sound settings")
    print("   2. Increase microphone volume to 80%+")
    print("   3. Try a different microphone")
    print("   4. Check app permissions (Windows/Mac)")

elif max_amp < 0.01:
    print("   ⚠️  MICROPHONE TOO QUIET")
    print("\n   Your microphone is working but too quiet for VAD.")
    print("\n   Solutions:")
    print("   1. Increase system microphone volume")
    print("   2. Speak louder and closer to mic")
    print("   3. In .env file, set: VAD_AGGRESSIVENESS=1")
    print("   4. Or use Press-to-Speak mode instead")

elif max_amp < 0.05:
    print("   ✅ MICROPHONE WORKING (Quiet)")
    print("\n   Your microphone works but voice is on the quiet side.")
    print("\n   Recommended settings:")
    print("   - VAD_AGGRESSIVENESS=1 (in .env)")
    print("   - Speak clearly at normal volume")

else:
    print("   ✅ MICROPHONE WORKING GREAT!")
    print("\n   Your microphone is detecting speech clearly.")
    print("\n   Recommended settings:")
    print("   - VAD_AGGRESSIVENESS=2 or 3 (in .env)")

# Test playback
print("\n" + "=" * 70)
print("🔊 Playing back your recording...")
print("=" * 70)

try:
    sd.play(audio, 16000)
    sd.wait()
    print("✅ Playback complete")
    print("\n💡 If you can't hear your voice clearly, your mic is too quiet.")
except Exception as e:
    print(f"❌ Playback error: {e}")

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)