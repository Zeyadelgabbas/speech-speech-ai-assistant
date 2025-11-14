import numpy as np
import webrtcvad
from collections import deque
from typing import Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceActivityDetector:
    """
    Detects voice activity in audio streams using WebRTC's VAD algorithm.
    
    This is used in continuous listening mode to:
    1. Detect when user starts speaking (trigger recording)
    2. Detect when user stops speaking (stop recording, send to STT)
    
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 3,
        frame_duration_ms: int = 30,
        padding_duration_ms: int = 750,
        speech_trigger_frames: int = 3
    ):
        """
        Initialize Voice Activity Detector.
        
        Args:
            sample_rate: Audio sample rate in Hz (must be 8000, 16000, 32000, or 48000)
            aggressiveness: VAD aggressiveness (0-3): 3 is most agressive 
               
            frame_duration_ms: Duration of each audio frame in milliseconds 
            padding_duration_ms: How long to keep recording after speech ends (ms)
            speech_trigger_frames: Number of consecutive speech frames needed to trigger
        
        Raises:
            ValueError: If sample_rate or frame_duration_ms are invalid
        """
        # Validate sample rate (WebRTC VAD only supports these)
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"Sample rate must be 8000, 16000, 32000, or 48000 Hz (got {sample_rate})")
        
        # Validate frame duration
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"Frame duration must be 10, 20, or 30 ms (got {frame_duration_ms})")
        
        # Validate agressivness
        if aggressiveness not in [0,1,2,3]:
            raise ValueError(f"agressivness must be 0, 1, 2, 3. got {aggressiveness}")
        
        self.sample_rate = sample_rate
        self.aggressiveness = aggressiveness
        self.frame_duration_ms = frame_duration_ms
        self.padding_duration_ms = padding_duration_ms
        self.speech_trigger_frames = speech_trigger_frames
        
        # Calculate frame size in samples 
        # i.e  how many samples are in one frame (samples in one second * frame duration in seconds)
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Calculate padding frames (how many silent frames to wait before stopping)
        self.padding_frames = int(round(padding_duration_ms / frame_duration_ms))
        
        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad(aggressiveness)
        
        # State tracking
        self.is_speech_active = False
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        
        # Ring buffer to store recent frames (for padding)
        self.ring_buffer = deque(maxlen=self.padding_frames)
        
        logger.info(
            f"VAD initialized: sample_rate={sample_rate}Hz, aggressiveness={aggressiveness}, "
            f"frame_duration={frame_duration_ms}ms, padding={padding_duration_ms}ms"
        )
    
    def _audio_to_bytes(self, audio: np.ndarray) -> bytes:
        """
        Convert float32 audio to 16-bit PCM bytes (required by WebRTC VAD).
        
        Args:
            audio: Audio as numpy array (float32, range -1.0 to 1.0)
        
        Returns:
            Audio as bytes (16-bit PCM, little-endian)
        
        Technical detail:
        WebRTC VAD expects raw PCM audio in 16-bit signed integer format.
        We convert float32 [-1.0, 1.0] to int16 [-32768, 32767].
        """
        # Clip to valid range and convert to int16
        audio_int16 = np.clip(audio, -1.0, 1.0) * 32767
        audio_int16 = audio_int16.astype(np.int16)
        
        # Convert to bytes (little-endian format expected by WebRTC)
        return audio_int16.tobytes()
    
    def is_speech(self, audio_frame: np.ndarray) -> bool:
        """
        Check if a single audio frame contains speech.
        
        Args:
            audio_frame: Audio frame as numpy array (must be exactly frame_size samples)
        
        Returns:
            True if speech detected, False if silence
        
        Raises:
            ValueError: If frame size is incorrect
        """
        if len(audio_frame) != self.frame_size:
            raise ValueError(
                f"Frame size mismatch: expected {self.frame_size} samples, got {len(audio_frame)}"
            )
        
        # Convert to bytes and run through VAD
        audio_bytes = self._audio_to_bytes(audio_frame)
        
        try:
            return self.vad.is_speech(audio_bytes, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD error: {e}")
            # On error, assume silence (safe default)
            return False
    
    def process_frame(self, audio_frame: np.ndarray) -> Tuple[bool, bool]:
        """
        Process a single audio frame and update VAD state.
        
        This implements a state machine with hysteresis (padding) to avoid
        cutting off speech too early or triggering on brief noises.
        
        Args:
            audio_frame: Audio frame as numpy array
        
        Returns:
            Tuple of (speech_started, speech_ended):
                speech_started: True if user just started speaking
                speech_ended: True if user just stopped speaking (after padding)
        
        State machine logic:
        - NOT SPEAKING → SPEAKING: After N consecutive speech frames (reduces false triggers)
        - SPEAKING → NOT SPEAKING: After M consecutive silence frames (padding prevents cutoff)
        """
        speech_detected = self.is_speech(audio_frame)
        
        speech_started = False
        speech_ended = False
        
        if not self.is_speech_active:
            # Currently in silence, waiting for speech to start
            if speech_detected:
                self.speech_frame_count += 1
                
                # Need multiple consecutive speech frames to trigger (avoid false positives)
                if self.speech_frame_count >= self.speech_trigger_frames:
                    self.is_speech_active = True
                    speech_started = True
                    self.speech_frame_count = 0
                    self.ring_buffer.clear()
                    logger.info("Speech started")
            else:
                self.speech_frame_count = 0
        
        else:
            # Currently speaking, waiting for silence
            if not speech_detected:
                self.silence_frame_count += 1
                
                # Need multiple consecutive silence frames to stop (padding)
                if self.silence_frame_count >= self.padding_frames:
                    self.is_speech_active = False
                    speech_ended = True
                    self.silence_frame_count = 0
                    logger.info(f"Speech ended (after {self.padding_duration_ms}ms padding)")
            else:
                # Still speaking, reset silence counter
                self.silence_frame_count = 0
        
        return speech_started, speech_ended
    
    def process_audio_buffer(self, audio: np.ndarray) -> Tuple[bool, bool, int]:
        """
        Process a buffer of audio (multiple frames) and return overall state.
        
        Args:
            audio: Audio buffer as numpy array (any length, will be split into frames)
        
        Returns:
            Tuple of (speech_started, speech_ended, speech_frame_count):
                speech_started: True if speech started in this buffer
                speech_ended: True if speech ended in this buffer
                speech_frame_count: Number of frames containing speech
        
        This is useful for processing recorded audio chunks in continuous mode.
        """
        speech_started = False
        speech_ended = False
        speech_frame_count = 0
        
        # Split audio into frames
        num_frames = len(audio) // self.frame_size
        
        for i in range(num_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio[start:end]
            
            frame_speech_started, frame_speech_ended = self.process_frame(frame)
            
            if frame_speech_started:
                speech_started = True
            
            if frame_speech_ended:
                speech_ended = True
            
            if self.is_speech(frame):
                speech_frame_count += 1
        
        return speech_started, speech_ended, speech_frame_count
    
    def reset(self):
        """Reset VAD state (useful when starting a new recording session)."""
        self.is_speech_active = False
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.ring_buffer.clear()
        logger.info("VAD state reset")
    
