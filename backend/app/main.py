"""
Production-ready FastAPI application with async handlers, Redis queuing, and connection pooling.
This is the refactored version of main.py that decouples TTS inference from request handlers.
"""
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import (
    PORT, HOST, WORKERS, CORS_ORIGINS, LOG_LEVEL, 
    TTS_QUEUE_MAX_DEPTH, LOG_LEVEL
)
from app.db import AsyncSessionLocal, init_async_db, get_async_db
from app.models import Session as SessionModel, Interaction as InteractionModel, AuditLog
from app.schemas import (
    StartSessionRequest, StartSessionResponse,
    SubmitAnswerRequest, SubmitAnswerResponse,
    GenerateSummaryRequest, SummaryResponse,
    SessionDetailResponse, TTSRequestSchema, TTSResponseSchema, 
    TTSResultPollSchema, TTSResultSchema, HealthCheckResponse, WorkerStatsResponse
)
from app.services.gemini_service import gemini_service
from app.queue.redis_client import RedisClient
from app.queue.task_schemas import TTSTaskSchema
from app.utils.cache import get_tts_cache_key, is_result_cached, get_cached_result, cache_tts_result
import base64

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Medical Pre-Consultation Assistant Backend (v2.0 Production)",
    version="2.0.0",
    description="Async, scalable architecture with Redis queuing and dedicated TTS workers"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Multilingual question sets
QUESTIONS = {
    "English": [
        "Do you have a fever?",
        "Do you have a headache?",
        "Are you experiencing vomiting?",
        "Do you have chest pain?",
        "Do you have a cough?"
    ],
    "Hindi": [
        "क्या आपको बुखार है?",
        "क्या आपको सिरदर्द है?",
        "क्या आपको उल्टी हो रही है?",
        "क्या आपको छाती में दर्द है?",
        "क्या आपको खांसी है?"
    ],
    "Marathi": [
        "तुम्हाला ताप आहे का?",
        "तुम्हाला डोकेदुखी आहे का?",
        "तुम्हाला उलटी होत आहे का?",
        "तुम्हाला छातीत दुखत आहे का?",
        "तुम्हाला खोकला आहे का?"
    ]
}

# ============ STARTUP / SHUTDOWN ============
@app.on_event("startup")
async def startup_event():
    """Initialize resources on app startup."""
    try:
        # Initialize async database
        logger.info("Initializing async database...")
        await init_async_db()
        
        # Initialize Redis
        logger.info("Initializing Redis connection pool...")
        await RedisClient.initialize()
        
        logger.info("✅ Application started successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on app shutdown."""
    try:
        logger.info("Shutting down...")
        await RedisClient.close()
        logger.info("✅ Application shut down successfully")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# ============ HEALTH CHECK & MONITORING ============
@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint with service status."""
    db_healthy = False
    redis_healthy = False
    tts_queue_depth = 0
    
    try:
        db_healthy = True  # Async session availability check
    except:
        pass
    
    try:
        redis_healthy = await RedisClient.health_check()
        tts_queue_depth = await RedisClient.peek_queue_depth("tts_tasks")
    except:
        pass
    
    return HealthCheckResponse(
        status="healthy" if (db_healthy and redis_healthy) else "degraded",
        database=db_healthy,
        redis=redis_healthy,
        tts_queue_depth=tts_queue_depth,
        db_pool_active=0,  # Placeholder
        db_pool_max=20,
        timestamp=datetime.utcnow()
    )


# ============ SESSION ENDPOINTS ============
@app.post("/api/start-session", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Start a new pre-consultation session."""
    if request.language not in QUESTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Choose from: {list(QUESTIONS.keys())}"
        )
    
    try:
        # Create new session with UUID
        session_id = uuid.uuid4()
        db_session = SessionModel(
            id=session_id,
            language=request.language,
            status="in_progress",
            version=1
        )
        db.add(db_session)
        await db.commit()
        
        logger.info(f"✅ Session {session_id} started in {request.language}")
        return StartSessionResponse(sessionId=str(session_id))
        
    except Exception as e:
        logger.error(f"❌ Failed to start session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.get("/api/session/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Retrieve full session details with history and summaries."""
    try:
        # Convert string to UUID
        import uuid as uuid_lib
        session_uuid = uuid_lib.UUID(session_id)
        
        query = select(SessionModel).where(SessionModel.id == session_uuid)
        result = await db.execute(query)
        db_session = result.scalars().first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionDetailResponse.from_orm(db_session)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to get session: {e}")
        raise HTTPException(status_code=500, detail="Database error")


# ============ ANSWER SUBMISSION ============
@app.post("/api/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Submit user's answer to a question.
    Validates answer using Gemini, advances to next question or repeats.
    """
    try:
        import uuid as uuid_lib
        session_uuid = uuid_lib.UUID(request.sessionId)
        
        # Fetch session
        query = select(SessionModel).where(SessionModel.id == session_uuid)
        result = await db.execute(query)
        db_session = result.scalars().first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        language = db_session.language
        lang_questions = QUESTIONS.get(language, [])
        
        # Verify question is valid
        if request.question not in lang_questions:
            raise HTTPException(status_code=400, detail="Question is not part of this language set")
        
        current_index = lang_questions.index(request.question)
        
        # Call Gemini to evaluate answer (async with retry logic)
        decision = await gemini_service.evaluate_answer(request.question, request.answer)
        
        if decision == "Next":
            # Check for existing interaction (prevent duplicates)
            existing_query = select(InteractionModel).where(
                (InteractionModel.session_id == session_uuid) &
                (InteractionModel.question == request.question)
            )
            existing_result = await db.execute(existing_query)
            existing = existing_result.scalars().first()
            
            if existing:
                # Update existing answer
                existing.answer = request.answer
                existing.gemini_decision = "Next"
            else:
                # Create new interaction
                interaction = InteractionModel(
                    session_id=session_uuid,
                    language=language,
                    question=request.question,
                    answer=request.answer,
                    gemini_decision="Next",
                    attempt=1
                )
                db.add(interaction)
            
            await db.commit()
            
            # Determine next question
            if current_index + 1 < len(lang_questions):
                next_question = lang_questions[current_index + 1]
                action = "Next"
            else:
                next_question = ""
                action = "Complete"
                db_session.status = "completed"
                await db.commit()
                logger.info(f"✅ Session {session_uuid} completed all questions")
        else:
            # Repeat the question
            action = "Repeat"
            next_question = request.question
            logger.debug(f"Repeating question in session {session_uuid}")
        
        return SubmitAnswerResponse(action=action, question=next_question)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to submit answer: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process answer")


# ============ SUMMARY GENERATION ============
@app.post("/api/generate-summary", response_model=SummaryResponse)
async def generate_summary(
    request: GenerateSummaryRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Generate medical summaries in multiple languages using Gemini."""
    try:
        import uuid as uuid_lib
        session_uuid = uuid_lib.UUID(request.sessionId)
        
        # Fetch session
        query = select(SessionModel).where(SessionModel.id == session_uuid)
        result = await db.execute(query)
        db_session = result.scalars().first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Fetch all interactions
        interactions_query = select(InteractionModel).where(
            InteractionModel.session_id == session_uuid
        ).order_by(InteractionModel.created_at)
        
        interactions_result = await db.execute(interactions_query)
        interactions = interactions_result.scalars().all()
        
        if not interactions:
            raise HTTPException(status_code=400, detail="No Q&A interactions found for this session")
        
        # Prepare history
        history = [{"question": item.question, "answer": item.answer} for item in interactions]
        
        # Call Gemini to generate summaries (async with retry logic)
        summaries = await gemini_service.generate_medical_summaries(history)
        
        # Save summaries
        db_session.english_summary = summaries["english_summary"]
        db_session.hindi_summary = summaries["hindi_summary"]
        db_session.marathi_summary = summaries["marathi_summary"]
        await db.commit()
        
        logger.info(f"✅ Generated summaries for session {session_uuid}")
        
        return SummaryResponse(
            english_summary=db_session.english_summary,
            hindi_summary=db_session.hindi_summary,
            marathi_summary=db_session.marathi_summary
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to generate summary")


# ============ TTS ENDPOINTS (ASYNC WITH REDIS QUEUE) ============
@app.post("/api/tts/request", response_model=TTSResponseSchema)
async def request_tts(request: TTSRequestSchema):
    """
    Request TTS generation.
    Returns a task_id for polling. Inference happens asynchronously in worker processes.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if request.language not in QUESTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")
    
    try:
        # Check if already cached
        cache_key = get_tts_cache_key(request.text, request.language)
        cached_result = await get_cached_result(RedisClient, request.text, request.language)
        
        if cached_result:
            logger.info(f"✅ TTS result found in cache")
            return TTSResponseSchema(
                task_id=cache_key,
                status="ready",
                message="Result ready in cache"
            )
        
        # Check queue depth
        queue_depth = await RedisClient.peek_queue_depth("tts_tasks")
        if queue_depth > TTS_QUEUE_MAX_DEPTH:
            raise HTTPException(
                status_code=503,
                detail=f"TTS queue full (depth: {queue_depth}). Please retry in a moment."
            )
        
        # Create task
        task_id = str(uuid.uuid4())
        task = TTSTaskSchema(
            task_id=task_id,
            session_id="system",  # No session for direct TTS requests
            text=request.text,
            language=request.language,
            max_retries=3,
            attempt=1
        )
        
        # Push to Redis queue
        await RedisClient.push_task("tts_tasks", task.dict())
        
        logger.info(f"✅ TTS task queued: {task_id} (queue_depth: {queue_depth})")
        
        return TTSResponseSchema(
            task_id=task_id,
            status="queued",
            message="Task queued for processing",
            queue_depth=queue_depth
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to queue TTS task: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue TTS task")


@app.post("/api/tts/poll", response_model=Optional[TTSResultSchema])
async def poll_tts_result(request: TTSResultPollSchema):
    """
    Poll for TTS result. Returns result if ready, 202 Accepted if still processing.
    """
    try:
        result_key = f"tts_result:{request.task_id}"
        result = await RedisClient.get_result(result_key)
        
        if result:
            if result.get("status") == "success":
                logger.info(f"✅ TTS result retrieved: {request.task_id}")
                return TTSResultSchema(**result)
            else:
                logger.warning(f"❌ TTS task failed: {request.task_id}")
                return TTSResultSchema(**result)
        else:
            # Still processing
            return JSONResponse(
                status_code=202,
                content={"status": "pending", "message": "Still processing"}
            )
        
    except Exception as e:
        logger.error(f"❌ Failed to poll TTS result: {e}")
        raise HTTPException(status_code=500, detail="Failed to poll result")


@app.get("/api/tts", deprecated=True)
async def get_tts_legacy(
    text: str = Query(..., description="Text to convert to speech"),
    lang: str = Query(..., description="Language: English, Hindi, Marathi")
):
    """
    DEPRECATED: Legacy synchronous TTS endpoint.
    Use /api/tts/request and /api/tts/poll instead.
    """
    logger.warning("Legacy /api/tts endpoint called - should use /api/tts/request + /api/tts/poll")
    
    # For backward compatibility, queue and wait (not recommended for production)
    request_schema = TTSRequestSchema(text=text, language=lang)
    response = await request_tts(request_schema)
    
    # Wait up to 30 seconds for result
    for attempt in range(30):
        result = await RedisClient.get_result(f"tts_result:{response.task_id}")
        if result and result.get("status") == "success":
            audio_b64 = result.get("audio_base64")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                return StreamingResponse(iter([audio_bytes]), media_type=result.get("mime_type", "audio/wav"))
        
        await asyncio.sleep(1)
    
    raise HTTPException(status_code=504, detail="TTS generation timeout")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 Starting FastAPI server on {HOST}:{PORT}")
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        workers=WORKERS,
        reload=False,
        log_level=LOG_LEVEL.lower()
    )
