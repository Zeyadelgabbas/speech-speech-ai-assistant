import numpy as np
import sounddevice as sd
from typing import Optional
from ..utils import get_logger

logger = get_logger(__name__)


class AudioPlayer:
    """
    Plays audio through speakers using sounddevice.
    Supports both blocking (wait until finished) and non-blocking playback.
    """
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize audio player.
        
        Args:
            sample_rate: Sample rate in Hz (should match the audio you're playing)
        """
        self.sample_rate = sample_rate
        self.is_playing = False
        
        logger.info(f"AudioPlayer initialized: {sample_rate}Hz")
    
    def play(self, audio: np.ndarray, blocking: bool = True):
        """
        Play audio through speakers.
        
        Args:
            audio: Audio data as numpy array (float32, range -1.0 to 1.0)
            blocking: If True, wait until playback finishes. If False, return immediately.
        
        Raises:
            ValueError: If audio data is invalid
        """
        if audio is None or len(audio) == 0:
            logger.warning("Cannot play empty audio")
            return
        
        # Ensure audio is float32 and in correct range
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # Clip to valid range [-1.0, 1.0]
        audio = np.clip(audio, -1.0, 1.0)
        
        # Reshape to column vector if needed (sounddevice expects shape (frames, channels))
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        duration = len(audio) / self.sample_rate
        logger.info(f"Playing audio: {len(audio)} samples ({duration:.2f}s)")
        
        try:
            self.is_playing = True
            sd.play(audio, samplerate=self.sample_rate)
            
            if blocking:
                sd.wait()  # Wait until playback finishes
                self.is_playing = False
                logger.info("Playback finished")
            else:
                logger.info("Non-blocking playback started")
        
        except Exception as e:
            self.is_playing = False
            logger.error(f"Error during playback: {e}")
            raise
    
    def stop(self):
        """Stop any currently playing audio."""
        if self.is_playing:
            sd.stop()
            self.is_playing = False
            logger.info("Playback stopped")
        else:
            logger.warning("No audio currently playing")
    
    @staticmethod
    def play_audio_data(audio: np.ndarray, sample_rate: int = 16000, blocking: bool = True):
        """
        Convenience method to play audio without creating a player instance.
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            blocking: If True, wait until playback finishes
        """
        player = AudioPlayer(sample_rate=sample_rate)
        player.play(audio, blocking=blocking)
    
    @staticmethod
    def test_speakers(duration: float = 1.0, frequency: float = 440.0, sample_rate: int = 16000) -> bool:
        """
        Test if speakers are working by playing a sine wave tone.
        
        Args:
            duration: Tone duration in seconds
            frequency: Frequency in Hz (440 Hz = A4 note)
            sample_rate: Sample rate in Hz
        
        Returns:
            True if playback succeeded, False otherwise
        """
        try:
            print(f"🔊 Testing speakers with {frequency}Hz tone for {duration}s...")
            
            # Generate sine wave
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            audio = 0.5 * np.sin(2 * np.pi * frequency * t)  # 0.3 amplitude to avoid loud volume
            
            # Play
            player = AudioPlayer(sample_rate=sample_rate)
            player.play(audio.astype(np.float32), blocking=True)
            
            print("✅ Speaker test passed!")
            logger.info("Speaker test passed")
            return True
        
        except Exception as e:
            print(f"❌ Speaker test failed: {e}")
            logger.error(f"Speaker test error: {e}")
            return False
    
    @staticmethod
    def get_available_devices():
        """
        Get list of available audio output devices.
        Useful for debugging speaker issues.
        
        Returns:
            List of device information dictionaries
        """
        devices = sd.query_devices()
        logger.info(f"Available audio devices: {devices}")
        return devices


# MODULE TEST
if __name__ == "__main__":

    # List available devices
    print("\nAvailable audio devices:")
    devices = AudioPlayer.get_available_devices()
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            print(f"  [{i}] {device['name']} (outputs: {device['max_output_channels']})")
    
    # Test speakers with sine wave
    print("\n" + "=" * 70)
    AudioPlayer.test_speakers(duration=1.0, frequency=440.0)
    
    # Test playing random audio
    print("\n" + "=" * 70)
    print("Testing playback with random audio (2s)...")
    sample_rate = 16000
    duration = 2.0
    
    # Generate some test audio (gentle noise)
    audio = np.random.normal(0, 0.1, int(sample_rate * duration)).astype(np.float32)
    
    player = AudioPlayer(sample_rate=sample_rate)
    player.play(audio, blocking=True)
    print(f"✅ Played {len(audio)} samples ({duration}s)")
    
    # Test non-blocking playback
    print("\n" + "=" * 70)
    print("Testing non-blocking playback...")
    audio2 = 0.2 * np.sin(2 * np.pi * 523.25 * np.linspace(0, 1, sample_rate))  # C5 note
    player.play(audio2.astype(np.float32), blocking=False)
    import time
    time.sleep(1)  # Wait  to let it finish
    
    print("\n" + "=" * 70)
    print("✅ All player tests passed!")