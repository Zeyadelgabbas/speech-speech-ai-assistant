import numpy as np
import wave
import io
import requests
import os
from pathlib import Path
from typing import Optional
from ..utils import config, get_logger

logger = get_logger(__name__)

class PiperTTS:


    VOICE_CATALOG = {
        "en_US-amy-low": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/low/en_US-amy-low.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/low/en_US-amy-low.onnx.json"
        },
        "en_US-amy-medium": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
        },
        "en_US-lessac-low": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx.json"
        },
        "en_US-lessac-medium": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        },
        "en_US-lessac-high": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx.json"
        },
        "en_GB-alan-low": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/low/en_GB-alan-low.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/low/en_GB-alan-low.onnx.json"
        },
        "en_GB-alan-medium": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"
        },
    }
    def __init__(self, voice: Optional[str] = None, speaker_id: Optional[int] = None):

        self.voice = voice or config.PIPER_VOICE
        self.speaker_id = speaker_id
        self.sample_rate = 22050
        self.voices_dir = config.VOICE_DIR
        
        self._ensure_voice_downloaded()

        from piper import PiperVoice
        voice_path = self.voices_dir / f"{self.voice}.onnx"
        config_path = self.voices_dir / f"{self.voice}.onnx.json"
        self.piper_voice = PiperVoice.load(str(voice_path),config_path=config_path)

        logger.info(f"✅ Loaded voice: {self.voice}")

    # ---------------------------------------------------------

    def _get_voice_paths(self) -> tuple[Path, Path]:
        """Get the expected paths for model and config files."""
        model_path = self.voices_dir / f"{self.voice}.onnx"
        config_path = self.voices_dir / f"{self.voice}.onnx.json"
        return model_path, config_path
    def _ensure_voice_downloaded(self):
        """Ensure the model (onnx + json) is downloaded locally."""
        model_path, config_path = self._get_voice_paths()

        if model_path.exists() and config_path.exists():
            logger.info(f"✅ Voice already downloaded: {self.voice}")
            return
        urls = self.VOICE_CATALOG[self.voice]
        
        logger.info(f"Downloading voice '{self.voice}'...")
        
        # Download model file
        logger.info(f"Downloading model file...")
        response = requests.get(urls["model"], stream=True)
        response.raise_for_status()
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Download config file
        logger.info(f"Downloading config file...")
        response = requests.get(urls["config"])
        response.raise_for_status()
        
        with open(config_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Voice downloaded successfully to {self.voices_dir}")

    # ---------------------------------------------------------
    def synthesize(self, text: str) -> np.ndarray:
        """Synthesize text to numpy audio array."""
        if not text.strip():
            return np.array([], dtype=np.float32)

        logger.info(f"Synthesizing: '{text[:50]}...'")

        try:
            # Piper now yields AudioChunk objects, not raw bytes
            audio_chunks = list(self.piper_voice.synthesize(text))
            audio = np.concatenate([chunk.audio_float_array for chunk in audio_chunks]).astype(np.float32)

            return audio
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise

# -------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("PIPER TTS TEST (AUTO DOWNLOAD + GENERATOR FIX)")
    print("=" * 70)

    try:
        tts = PiperTTS()
        print(f"✅ Initialized TTS with voice {tts.voice}")
        audio = tts.synthesize("Hello, this is a Piper test.")
        print(f"✅ Synthesized {len(audio)} samples.")
    except Exception as e:
        print(f"❌ Error: {e}")
