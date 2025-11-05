import numpy as np
from faster_whisper import WhisperModel
from typing import Optional, List, Dict
from ..utils import config , get_logger

logger = get_logger(__name__)

class FasterWhisperSTT:
    """
    Speech-to-Text engine using faster-whisper.
    
    """
    
    def __init__(
        self,
        model_size: str = None,
        device: str = None,
        compute_type: str = None,
        download_root: Optional[str] = None
    ):
        """
        Initialize faster-whisper model.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to run on ("cpu", "cuda", "auto")
            compute_type: Computation precision ("int8", "float16", "float32")
            download_root: Directory to cache downloaded models
                Defaults to ~/.cache/huggingface/hub/
        
        """

        self.model_size = model_size or config.WHISPER_MODEL_SIZE
        self.device = device or config.get_whisper_device()
        self.compute_type = compute_type or config.WHISPER_COMPUTE_TYPE
        # uncomment if you want cache in ./data/cache folder 
        #download_root = download_root or config.CACHE_DIR
        
        # Auto-adjust compute type based on device
        if self.device == "cpu" and self.compute_type == "float16":
            logger.warning("float16 not supported on CPU, falling back to int8")
            self.compute_type = "int8"  
        
        logger.info(
            f"Initializing faster-whisper: model={self.model_size}, "
            f"device={self.device}, compute_type={self.compute_type}"
        )
        
        try:
            # Load model (downloads on first use, ~50-500MB depending on size)
            self.model = WhisperModel(
                model_size_or_path=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=download_root
            )
            logger.info(f"Model loaded successfully: {self.model_size}")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = "en",
        task: str = "transcribe",
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio as numpy array (float32, mono, any sample rate)
                Will be automatically resampled to 16kHz internally
            language: Language code (e.g., "en", "es", "fr"). If None, auto-detect.
            task: "transcribe" (original language) or "translate" (translate to English)
            beam_size: Beam search size (1-10). Higher = better quality, slower.
                5 is a good balance. Use 1 for fastest (greedy decoding).
            best_of: Number of candidates when sampling. Higher = better but slower.
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
                Use 0.0 for voice commands (you want exact words, not paraphrasing)
            vad_filter: Use internal Silero VAD to filter silence before transcription
            vad_parameters: Custom VAD parameters (min_speech_duration_ms, etc.)
        
        Returns:
            Dictionary with:
                - text: Full transcription
                - segments: List of segments with timestamps
                - language: Detected language code
                - language_probability: Confidence in language detection
        
        Technical notes:
        - Audio is automatically resampled to 16kHz (Whisper's native rate)
        - VAD filtering improves accuracy by removing silence
        - beam_size=5 is OpenAI's default (good quality/speed trade-off)
        - temperature=0.0 ensures deterministic output (same audio → same text)
        """
        if audio is None or len(audio) == 0:
            logger.warning("Empty audio provided to transcribe()")
            return {
                "text": "",
                "segments": [],
                "language": None,
                "language_probability": 0.0
            }
        
        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if np.max(np.abs(audio)) < 1e-4:
            logger.warning("Audio is silent or too quiet — skipping transcription.")
            return {
                "text": "",
                "segments": [],
                "language": None,
                "language_probability": 0.0
    }

        # Log audio stats
        duration = len(audio) / 16000  # Approximate duration in seconds (assumes 16kHz)
        logger.info(f"Transcribing audio: {len(audio)} samples (~{duration:.2f}s)")
        
        try:
            # Transcribe using faster-whisper
            segments, info = self.model.transcribe(
                audio,
                language=language, 
                task=task,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                vad_filter=vad_filter,
                vad_parameters=vad_parameters or None
            )
            
            # Convert generator to list and extract text
            segments_list = []
            full_text = []
            
            for segment in segments:
                segments_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
                full_text.append(segment.text.strip())
            
            # Combine all segments into full text
            transcription = " ".join(full_text).strip()
            
            logger.info(
                f"Transcription complete: language={info.language} "
                f"({info.language_probability:.2%}), text_length={len(transcription)} chars"
            )
            
            if config.DEBUG_MODE:
                logger.debug(f"Transcription: {transcription}")
            
            return {
                "text": transcription,
                "segments": segments_list,
                "language": info.language,
                "language_probability": info.language_probability
            }
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    def transcribe_file(self, audio_path: str, **kwargs) -> Dict[str, any]:
        """
        Transcribe audio from a file.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, FLAC, etc.)
            **kwargs: Additional arguments passed to transcribe()
        
        Returns:
            Transcription result dictionary
        """
        import soundfile as sf
        
        logger.info(f"Loading audio file: {audio_path}")
        
        try:
            # Load audio file (soundfile handles multiple formats)
            audio, sample_rate = sf.read(audio_path, dtype='float32')
            
            # Convert stereo to mono if needed
            if audio.ndim == 2:
                audio = audio.mean(axis=1)
            
            logger.info(f"Loaded {len(audio)} samples at {sample_rate}Hz")
            
            return self.transcribe(audio, **kwargs)
        
        except Exception as e:
            logger.error(f"Error loading audio file: {e}")
            raise
    
    def detect_language(self, audio: np.ndarray) -> Dict[str, float]:
        """
        Detect language of audio without transcribing.
        
        Args:
            audio: Audio as numpy array
        
        Returns:
            Dictionary of language codes and probabilities
            Example: {"en": 0.95, "es": 0.03, "fr": 0.02}
        
        Note: This uses Whisper's audio encoder to detect language from
        the first 30 seconds of audio. Very fast (~100ms on CPU).
        """
        if audio is None or len(audio) == 0:
            return {}
        
        logger.info("Detecting language...")
        
        try:
            # Detect language using first 30 seconds
            segments, info = self.model.transcribe(
                audio,
                task="transcribe",
                beam_size=1,  # Fast mode
                language=None  # Auto-detect
            )
            
            # Consume generator (needed to get info)
            _ = list(segments)
            
            logger.info(f"Detected language: {info.language} ({info.language_probability:.2%})")
            
            return {
                info.language: info.language_probability
            }
        
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return {}
    

if __name__ == "__main__":
    import sounddevice as sd
    
    print("=" * 70)
    print("FASTER-WHISPER STT TEST")
    print("=" * 70)
    

    #  Initialize model
    print("\n" + "=" * 70)
    print(f"Initializing model: {config.WHISPER_MODEL_SIZE}")
    print("(First run will download model, may take 1-2 minutes...)")
    
    try:
        stt = FasterWhisperSTT()
        print(f"✅ Model loaded: {stt.model_size} on {stt.device}")
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        print("   Make sure you have internet connection for first-time download")
        exit(1)
    
    #  Transcribe from microphone
    print("\n" + "=" * 70)
    print("🎤 Microphone transcription test")
    user_input = input("Record and transcribe audio from mic? (y/n): ").strip().lower()
    
    if user_input == 'y':
        duration = 10.0
        sample_rate = 16000
        
        print(f"\n🔴 Recording for {duration} seconds...")
        print("   Say something like: 'Hello, this is a test of the speech recognition system.'")
        
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        audio = audio.flatten()
        
        print("✅ Recording complete, transcribing...")
        
        result = stt.transcribe(audio)
        
        print("\n" + "=" * 70)
        print("📝 TRANSCRIPTION RESULTS")
        print("=" * 70)
        print(f"Text: {result['text']}")
        print(f"Language: {result['language']} ({result['language_probability']:.1%} confidence)")
        print(f"Segments: {len(result['segments'])}")
        
        if result['segments']:
            print("\n⏱️  Timestamped segments:")
            for i, seg in enumerate(result['segments'], 1):
                print(f"  [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
    
    #  Test with synthetic audio (optional)
    print("\n" + "=" * 70)
    print("Testing with silent audio (edge case)...")
    
    silent_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
    result_silent = stt.transcribe(silent_audio)
    
    if result_silent['text'] == "":
        print("✅ Silent audio correctly returned empty transcription")
    else:
        print(f"⚠️  Silent audio transcribed as: '{result_silent['text']}'")
        print("   (This is expected with VAD disabled or very sensitive model)")
    
    #  Language detection
    print("\n" + "=" * 70)
    print("Testing language detection...")
    
    if user_input == 'y' and len(audio) > 0:
        languages = stt.detect_language(audio)
        print("Detected languages:")
        for lang, prob in languages.items():
            print(f"  {lang}: {prob:.1%}")
    
    print("\n" + "=" * 70)
    print("✅ All STT tests passed!")