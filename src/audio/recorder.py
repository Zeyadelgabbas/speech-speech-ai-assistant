import numpy as np
import sounddevice as sd
from typing import Optional
from ..utils import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """
    Records audio from microphone using sounddevice.
    Supports both press-to-talk (manual start/stop) and continuous recording.
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio recorder.
        
        Args:
            sample_rate: Sample rate in Hz (16000 is optimal for Whisper)
            channels: Number of audio channels (1 = mono, 2 = stereo)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording: Optional[list] = None
        self.is_recording = False
        
        logger.info(f"AudioRecorder initialized: {sample_rate}Hz, {channels} channel(s)")
    
    def start_recording(self):
        """Start recording audio."""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return
        
        self.recording = []
        self.is_recording = True
        logger.info("Recording started")
    
    def record_chunk(self, duration: float = 0.5) -> np.ndarray:
        """
        Record a single chunk of audio.
        
        Args:
            duration: Duration in seconds to record
        
        Returns:
            numpy array of audio samples (float32, range -1.0 to 1.0)
        """
        try:
            num_samples = int(round(duration*self.sample_rate))

            audio_chunk = sd.rec(
                int(round(duration * self.sample_rate)),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32'
            )
            sd.wait()  # Wait until recording is finished
            
            # Convert to mono if stereo
            if audio_chunk.ndim == 2:

                if self.channels ==2 and audio_chunk[1]==2:
                    audio_chunk= audio_chunk.mean(axis=1)

                elif audio_chunk[1]==1:
                    audio_chunk=audio_chunk.flatten()
                
                elif audio_chunk[1] ==2 and self.channels==1:
                    logger.warning(f"Device is stereo but mon is requested")
                    audio_chunk = audio_chunk.mean(axis=1)

            audio_chunk = audio_chunk.flatten()

            if len(audio_chunk) != num_samples:
                logger.warning(f"Sample count mismatch expected: {num_samples} got : {len(audio_chunk)}")
            
            return audio_chunk
        
        except Exception as e:
            logger.error(f"Error recording chunk: {e}")
            raise
    
    def add_chunk(self, chunk: np.ndarray):
        """
        Add an audio chunk to the current recording.
        
        Args:
            chunk: Audio data as numpy array
        """
        if not self.is_recording:
            logger.warning("Not currently recording, call start_recording() first")
            return
        
        self.recording.append(chunk)
    
    def stop_recording(self) -> np.ndarray:
        """
        Stop recording and return the complete audio.
        
        Returns:
            numpy array of complete audio recording
        """
        if not self.is_recording:
            logger.warning("No recording in progress")
            return np.array([])
        
        self.is_recording = False
        
        if not self.recording:
            logger.warning("No audio chunks recorded")
            return np.array([])
        
        # Concatenate all chunks
        complete_audio = np.concatenate(self.recording)
        logger.info(f"Recording stopped: {len(complete_audio)} samples ({len(complete_audio)/self.sample_rate:.2f}s)")
        
        return complete_audio
    
    def record_fixed_duration(self, duration: float) -> np.ndarray:
        """
        Record audio for a fixed duration (blocking).
        Convenience method for simple recording.
        
        Args:
            duration: Duration in seconds
        
        Returns:
            numpy array of audio samples
        """
        logger.info(f"Recording for {duration}s...")
        
        try:
            audio = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32'
            )
            sd.wait()
            
            # Convert to mono if stereo
            if self.channels == 2:
                audio = audio.mean(axis=1)
            
            audio = audio.flatten()
            logger.info(f"Recorded {len(audio)} samples ({duration}s)")
            
            return audio
        
        except Exception as e:
            logger.error(f"Error during fixed duration recording: {e}")
            raise
    
    @staticmethod
    def get_available_devices():
        """
        Get list of available audio input devices.
        Useful for debugging microphone issues.
        
        Returns:
            List of device information dictionaries
        """
        devices = sd.query_devices()
        logger.info(f"Available audio devices: {devices}")
        return devices
    
    @staticmethod
    def test_microphone(duration: float = 2.0, sample_rate: int = 16000) -> bool:
        """
        Test if microphone is working by recording a short clip.
        
        Args:
            duration: Test duration in seconds
            sample_rate: Sample rate in Hz
        
        Returns:
            True if microphone works, False otherwise
        """
        try:
            print(f"🎤 Testing microphone for {duration}s... Speak now!")
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()
            
            # Check if audio was captured (not all zeros/silence)
            max_amplitude = np.abs(audio).max()
            
            if max_amplitude < 0.001:
                print("❌ Microphone test failed: No audio detected (too quiet or mic not working)")
                logger.error("Microphone test failed: no audio signal")
                return False
            
            print(f"✅ Microphone test passed! Max amplitude: {max_amplitude:.4f}")
            logger.info(f"Microphone test passed: max_amplitude={max_amplitude:.4f}")
            return True
        
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            logger.error(f"Microphone test error: {e}")
            return False



# MODULE TEST
if __name__ == "__main__":
    print("=" * 70)
    print("AUDIO RECORDER TEST")
    print("=" * 70)
    
    # List available devices
    print("\n📋 Available audio devices:")
    devices = AudioRecorder.get_available_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']} (inputs: {device['max_input_channels']})")
    
    # Test microphone
    print("\n" + "=" * 70)
    AudioRecorder.test_microphone(duration=2.0)
    
    # Test fixed duration recording
    print("\n" + "=" * 70)
    print("Testing 3-second recording...")
    recorder = AudioRecorder(sample_rate=16000)
    audio = recorder.record_fixed_duration(duration=3.0)
    print(f"✅ Recorded {len(audio)} samples ({len(audio)/16000:.2f}s)")
    print(f"   Audio range: {audio.min():.4f} to {audio.max():.4f}")
    
    # Test chunked recording
    print("\n" + "=" * 70)
    print("Testing chunked recording (3 chunks of 1s each)...")
    recorder.start_recording()
    for i in range(3):
        print(f"  Recording chunk {i+1}/3...")
        chunk = recorder.record_chunk(duration=1.0)
        recorder.add_chunk(chunk)
    
    complete_audio = recorder.stop_recording()
    print(f"✅ Complete recording: {len(complete_audio)} samples ({len(complete_audio)/16000:.2f}s)")
    
    print("\n" + "=" * 70)
    print("✅ All recorder tests passed!")