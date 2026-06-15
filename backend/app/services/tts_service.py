import io
import logging
import json
import numpy as np
import soundfile as sf
from gtts import gTTS
from app.config import OMNIVOICE_API_URL

logger = logging.getLogger(__name__)

class TTSService:
    _model = None
    _device = None

    @staticmethod
    def _load_model():
        """Load OmniVoice model lazily, using GPU if available, otherwise CPU."""
        if TTSService._model is not None:
            return TTSService._model
        try:
            from omnivoice import OmniVoice
            import torch
            # Determine device map
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
        """Return the absolute path to the reference audio for the given language.
        Expected language values: English, Hindi, Marathi (case‑insensitive)."""
        lang = language.lower()
        if "hindi" in lang:
            return r"C:\Users\Acer\Downloads\hindi_ref.mp3"
        if "marathi" in lang:
            return r"C:\Users\Acer\Downloads\marathi_ref.wav"
        # Default to English reference
        return r"C:\Users\Acer\Downloads\eng_ref.mp3"

    @staticmethod
    def generate_speech(text: str, language: str) -> tuple[bytes, str]:
        """Generate speech audio for *text* in the requested *language*.
        The function tries the local OmniVoice model first (GPU preferred, CPU fallback).
        If that fails, it falls back to gTTS.
        Returns a tuple ``(audio_bytes, mime_type)``.
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
                # OmniVoice returns a list of NP arrays at 24 kHz
                wav_buffer = io.BytesIO()
                # Write the first array; if multiple, they can be concatenated
                sf.write(wav_buffer, audio_list[0], 24000, format="WAV")
                return wav_buffer.getvalue(), "audio/wav"
            except Exception as e:
                logger.error(f"OmniVoice synthesis failed: {e}")
                # fall through to gTTS fallback

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
