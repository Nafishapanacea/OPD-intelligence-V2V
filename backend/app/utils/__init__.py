# Utils module initialization
from app.utils.cache import (
    compute_audio_hash,
    encode_audio_base64,
    decode_audio_base64,
    get_tts_cache_key,
    is_result_cached,
    get_cached_result,
    cache_tts_result,
    should_cache_tts
)

__all__ = [
    "compute_audio_hash",
    "encode_audio_base64",
    "decode_audio_base64",
    "get_tts_cache_key",
    "is_result_cached",
    "get_cached_result",
    "cache_tts_result",
    "should_cache_tts"
]
