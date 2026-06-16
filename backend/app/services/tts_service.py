"""
TTS Service with caching support.
Inference is now handled by dedicated worker processes.
"""
import io
import logging
import json
import numpy as np
import soundfile as sf
from gtts import gTTS

logger = logging.getLogger(__name__)


class TTSService:
    """Handles TTS generation with caching and fallback strategies."""
    
    _model = None
    _device = None

    @staticmethod
    def _load_model():
        """
        Load OmniVoice model lazily on first inference request from worker process.
        This should only be called from worker processes, NOT from FastAPI handlers.
        """
        if TTSService._model is not None:
            return TTSService._model
        
        try:
            from omnivoice import OmniVoice
            import torch
            
            device_map = "cuda:0" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            TTSService._model = OmniVoice.from_pretrained(
                "k2-fsa/OmniVoice",
                device_map=device_map,
                dtype=dtype,
            )
            TTSService._device = device_map
            logger.info(f"OmniVoice model loaded on {device_map}.")
            
        except Exception as e:
            logger.error(f"Failed to load OmniVoice model: {e}")
            TTSService._model = None
        
        return TTSService._model

    @staticmethod
    def _reference_path(language: str) -> str:
        """Return the absolute path to the reference audio for the given language."""
        lang = language.lower()
        if "hindi" in lang:
            return r"C:\Users\Acer\Downloads\hindi_ref.mp3"
        if "marathi" in lang:
            return r"C:\Users\Acer\Downloads\marathi_ref.wav"
        # Default to English reference
        return r"C:\Users\Acer\Downloads\eng_ref.mp3"

    @staticmethod
    def generate_speech(text: str, language: str) -> tuple:
        """
        Generate speech audio using OmniVoice with fallback to gTTS.
        
        ⚠️  IMPORTANT: This method should ONLY be called from TTS worker processes,
        NOT from FastAPI request handlers. FastAPI handlers should queue tasks instead.
        
        Returns:
            tuple: (audio_bytes, mime_type)
        """
        # 1️⃣ Attempt OmniVoice synthesis
        model = TTSService._load_model()
        if model is not None:
            try:
                ref_path = TTSService._reference_path(language)
                logger.info(
                    f"Generating speech via OmniVoice (language={language}, ref={ref_path})"
                )
                audio_list = model.generate(text=text, ref_audio=ref_path)
                
                # OmniVoice returns a list of NP arrays at 24 kHz
                wav_buffer = io.BytesIO()
                sf.write(wav_buffer, audio_list[0], 24000, format="WAV")
                return wav_buffer.getvalue(), "audio/wav"
                
            except Exception as e:
                logger.error(f"OmniVoice synthesis failed: {e}")
                # Fall through to gTTS fallback

        # 2️⃣ gTTS fallback (language codes mapping)
        lang_map = {"hindi": "hi", "marathi": "mr"}
        gtts_code = lang_map.get(language.lower(), "en")
        logger.info(
            f"Falling back to gTTS for language '{language}' (code={gtts_code})"
        )
        try:
            tts = gTTS(text=text, lang=gtts_code, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            return fp.getvalue(), "audio/mpeg"
            
        except Exception as e:
            logger.error(f"gTTS generation failed: {e}")
            # Final fallback: return 1‑second silent wav to avoid breaking client
            silent_wav = (
                b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
                b"\x01\x00\x08\x00data\x00\x00\x00\x00"
            )
            return silent_wav, "audio/wav"

    @staticmethod
    async def generate_speech_async(text: str, language: str) -> tuple:
        """
        Async wrapper for generate_speech (runs in thread executor).
        Called by worker processes when needed.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: TTSService.generate_speech(text, language)
        )

