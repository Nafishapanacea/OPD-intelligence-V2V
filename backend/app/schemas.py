from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

# --- Request / Response for starting session ---
class StartSessionRequest(BaseModel):
    language: str = Field(..., description="Selected language: English, Hindi, or Marathi")

class StartSessionResponse(BaseModel):
    sessionId: str = Field(..., description="Unique session identifier")


# --- Request / Response for submitting an answer ---
class SubmitAnswerRequest(BaseModel):
    sessionId: str = Field(..., description="Active session ID")
    question: str = Field(..., description="The question that was asked")
    answer: str = Field(..., description="The user's spoken or textual answer")

class SubmitAnswerResponse(BaseModel):
    action: str = Field(..., description="Decision action: 'Next' or 'Repeat'")
    question: str = Field(..., description="The next question to read, or the repeated question")


# --- Request / Response for final summary generation ---
class GenerateSummaryRequest(BaseModel):
    sessionId: str = Field(..., description="Session ID to compile history and generate summaries for")

class SummaryResponse(BaseModel):
    english_summary: str = Field(..., description="Medical intake summary in English")
    hindi_summary: str = Field(..., description="Medical intake summary in Hindi")
    marathi_summary: str = Field(..., description="Medical intake summary in Marathi")


# --- Interaction history structures ---
class InteractionDetail(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Complete session details structure ---
class SessionDetailResponse(BaseModel):
    id: str
    language: str
    english_summary: Optional[str] = None
    hindi_summary: Optional[str] = None
    marathi_summary: Optional[str] = None
    created_at: datetime
    interactions: List[InteractionDetail] = []

    class Config:
        from_attributes = True
