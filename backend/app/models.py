import datetime
import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, BigInteger, LargeBinary, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base


class Session(Base):
    """Patient consultation session."""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    language = Column(String(50), nullable=False)
    status = Column(String(20), default="in_progress")  # in_progress, completed, archived
    
    # Summaries in multiple languages
    english_summary = Column(Text, nullable=True)
    hindi_summary = Column(Text, nullable=True)
    marathi_summary = Column(Text, nullable=True)
    
    # Optimistic locking: version increments on each update
    version = Column(Integer, default=1, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship to interactions
    interactions = relationship("Interaction", back_populates="session", cascade="all, delete-orphan")
    
    # Index for querying sessions by status
    __table_args__ = (
        Index('idx_sessions_status_created', 'status', 'created_at'),
    )


class Interaction(Base):
    """Question-answer pair for a session."""
    __tablename__ = "interactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    language = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    
    # Gemini decision: "Next" or the question text (for repeat)
    gemini_decision = Column(String(20), nullable=True)
    
    # Track if question was repeated
    attempt = Column(Integer, default=1)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship back to session
    session = relationship("Session", back_populates="interactions")
    
    # Prevent duplicate Q&A pairs in same session
    __table_args__ = (
        Index('idx_interactions_session_question_attempt', 'session_id', 'question', 'attempt', unique=True),
        Index('idx_interactions_created_at', 'created_at'),
    )


class TTSCache(Base):
    """Cache for frequently requested TTS audio."""
    __tablename__ = "tts_cache"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    audio_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA256
    audio_duration_ms = Column(Integer, nullable=True)
    cache_hits = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    __table_args__ = (
        Index('idx_tts_cache_text_language', 'text', 'language'),
    )


class AuditLog(Base):
    """Audit log for detecting concurrent access issues."""
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    interaction_id = Column(BigInteger, ForeignKey("interactions.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # update, delete, concurrent_conflict
    old_data = Column(Text, nullable=True)  # JSON
    new_data = Column(Text, nullable=True)  # JSON
    request_id = Column(String(36), nullable=True, index=True)  # UUID for tracing
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_audit_log_session_id_timestamp', 'session_id', 'timestamp'),
    )
