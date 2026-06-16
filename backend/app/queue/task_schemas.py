"""Pydantic schemas for Redis queue tasks."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TTSTaskSchema(BaseModel):
    """Schema for TTS (Text-to-Speech) inference tasks."""
    task_id: str = Field(..., description="Unique task ID (UUID)")
    session_id: str = Field(..., description="Session ID for tracing")
    text: str = Field(..., description="Text to convert to speech")
    language: str = Field(..., description="Language: English, Hindi, Marathi")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    max_retries: int = Field(default=3, description="Max retry attempts")
    attempt: int = Field(default=1, description="Current attempt number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "uuid-session",
                "text": "Do you have a fever?",
                "language": "English",
                "timestamp": 1623456789.0,
                "max_retries": 3,
                "attempt": 1
            }
        }


class TTSResultSchema(BaseModel):
    """Schema for TTS result stored in Redis cache."""
    task_id: str
    status: str = Field(..., description="'success' or 'failed'")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio data")
    mime_type: str = Field(default="audio/wav")
    error: Optional[str] = None
    processing_time_ms: int = Field(..., description="Time taken to process")
    created_at: datetime
    attempt: int = Field(default=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "success",
                "audio_base64": "UklGRiYAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQIAAAAAAA==",
                "mime_type": "audio/wav",
                "processing_time_ms": 2500,
                "created_at": "2024-01-01T12:00:00Z",
                "attempt": 1
            }
        }


class GeminiTaskSchema(BaseModel):
    """Schema for Gemini API async tasks (future use)."""
    task_id: str
    session_id: str
    prompt: str
    model: str = Field(default="gemini-2.5-flash")
    temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=50)
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    max_retries: int = Field(default=3)
    attempt: int = Field(default=1)
