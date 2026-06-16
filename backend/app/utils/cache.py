"""Utility functions for TTS caching and deduplication."""
import hashlib
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def compute_audio_hash(audio_bytes: bytes) -> str:
    """Compute SHA256 hash of audio data for deduplication."""
    return hashlib.sha256(audio_bytes).hexdigest()


def encode_audio_base64(audio_bytes: bytes) -> str:
    """Encode audio bytes to base64 string for JSON storage."""
    return base64.b64encode(audio_bytes).decode('utf-8')


def decode_audio_base64(audio_b64: str) -> bytes:
    """Decode base64 audio string back to bytes."""
    return base64.b64decode(audio_b64)


def get_tts_cache_key(text: str, language: str) -> str:
    """Generate cache key for TTS result."""
    # Hash text to avoid long keys
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"tts_result:{language}:{text_hash}"


async def is_result_cached(redis_client, text: str, language: str) -> bool:
    """Check if TTS result already cached."""
    cache_key = get_tts_cache_key(text, language)
    result = await redis_client.get_result(cache_key)
    return result is not None


async def get_cached_result(redis_client, text: str, language: str) -> Optional[dict]:
    """Retrieve cached TTS result."""
    cache_key = get_tts_cache_key(text, language)
    return await redis_client.get_result(cache_key)


async def cache_tts_result(redis_client, text: str, language: str, 
                          audio_bytes: bytes, mime_type: str) -> bool:
    """Cache TTS result in Redis."""
    cache_key = get_tts_cache_key(text, language)
    
    result = {
        "audio_base64": encode_audio_base64(audio_bytes),
        "mime_type": mime_type,
        "text_hash": hashlib.md5(text.encode()).hexdigest(),
        "language": language
    }
    
    return await redis_client.set_result(cache_key, result, ttl=7 * 24 * 3600)  # 7 days


def should_cache_tts(text: str) -> bool:
    """Determine if TTS result should be cached."""
    # Cache if text is longer than 10 chars (avoid caching tiny fragments)
    return len(text.strip()) > 10
