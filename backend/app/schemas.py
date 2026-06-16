from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID


# ============ SESSION MANAGEMENT ============
class StartSessionRequest(BaseModel):
    language: str = Field(..., description="Selected language: English, Hindi, or Marathi")


class StartSessionResponse(BaseModel):
    sessionId: str = Field(..., description="Unique session identifier (UUID)")


# ============ ANSWER SUBMISSION ============
class SubmitAnswerRequest(BaseModel):
    sessionId: str = Field(..., description="Active session ID")
    question: str = Field(..., description="The question that was asked")
    answer: str = Field(..., description="The user's spoken or textual answer")


class SubmitAnswerResponse(BaseModel):
    action: str = Field(..., description="Decision action: 'Next', 'Repeat', or 'Complete'")
    question: str = Field(..., description="The next question to read, or the repeated question")


# ============ SUMMARY GENERATION ============
class GenerateSummaryRequest(BaseModel):
    sessionId: str = Field(..., description="Session ID to compile history and generate summaries for")


class SummaryResponse(BaseModel):
    english_summary: str = Field(..., description="Medical intake summary in English")
    hindi_summary: str = Field(..., description="Medical intake summary in Hindi")
    marathi_summary: str = Field(..., description="Medical intake summary in Marathi")


# ============ INTERACTION HISTORY ============
class InteractionDetail(BaseModel):
    id: int
    question: str
    answer: str
    gemini_decision: Optional[str] = None
    attempt: int = 1
    timestamp: datetime

    class Config:
        from_attributes = True


# ============ SESSION DETAILS ============
class SessionDetailResponse(BaseModel):
    id: str
    language: str
    status: str = "in_progress"
    english_summary: Optional[str] = None
    hindi_summary: Optional[str] = None
    marathi_summary: Optional[str] = None
    version: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None
    interactions: List[InteractionDetail] = []

    class Config:
        from_attributes = True


# ============ TTS ENDPOINTS ============
class TTSRequestSchema(BaseModel):
    """Request for TTS generation (used by client)."""
    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=1000)
    language: str = Field(..., description="Language: English, Hindi, or Marathi")


class TTSResponseSchema(BaseModel):
    """Response for TTS generation (queued task)."""
    task_id: str = Field(..., description="Unique task ID for polling result")
    status: str = Field(..., description="'queued' or 'error'")
    message: Optional[str] = None
    queue_depth: Optional[int] = None


class TTSResultPollSchema(BaseModel):
    """Result polling schema."""
    task_id: str = Field(..., description="Task ID to poll for result")


class TTSResultSchema(BaseModel):
    """TTS result when ready."""
    task_id: str
    status: str  # 'success', 'failed', 'pending'
    audio_base64: Optional[str] = None
    mime_type: str = "audio/wav"
    error: Optional[str] = None
    processing_time_ms: int
    created_at: datetime
    attempt: int = 1

    class Config:
        from_attributes = True


# ============ HEALTH CHECK ============
class HealthCheckResponse(BaseModel):
    status: str
    database: bool
    redis: bool
    tts_queue_depth: int
    db_pool_active: int
    db_pool_max: int
    timestamp: datetime


class WorkerStatsResponse(BaseModel):
    worker_type: str
    status: str
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime_s: float
    last_task_at: Optional[datetime] = None

