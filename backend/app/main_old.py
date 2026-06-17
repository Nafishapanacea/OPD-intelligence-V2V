import uuid
import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.config import PORT
from app.db import Base, engine, get_db
from app.models import Session as SessionModel, Interaction as InteractionModel
from app.schemas import (
    StartSessionRequest, StartSessionResponse,
    SubmitAnswerRequest, SubmitAnswerResponse,
    GenerateSummaryRequest, SummaryResponse,
    SessionDetailResponse
)
from app.services.gemini_service import GeminiService
from app.services.tts_service import TTSService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Medical Pre-Consultation Assistant Backend", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate services
gemini_service = GeminiService()

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

@app.post("/api/start-session", response_model=StartSessionResponse)
def start_session(request: StartSessionRequest, db: DBSession = Depends(get_db)):
    """
    Starts a new pre-consultation session and registers the patient's language.
    """
    if request.language not in QUESTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported language. Choose from: {list(QUESTIONS.keys())}")
    
    session_id = str(uuid.uuid4())
    db_session = SessionModel(id=session_id, language=request.language)
    db.add(db_session)
    db.commit()
    
    logger.info(f"Started session {session_id} in {request.language}")
    return StartSessionResponse(sessionId=session_id)


@app.post("/api/submit-answer", response_model=SubmitAnswerResponse)
def submit_answer(request: SubmitAnswerRequest, db: DBSession = Depends(get_db)):
    """
    Validates the user's spoken answer using the Gemini decision engine.
    If valid -> saves the QA pair to database and advances to the next question.
    If invalid -> repeats the same question.
    """
    db_session = db.query(SessionModel).filter(SessionModel.id == request.sessionId).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    language = db_session.language
    lang_questions = QUESTIONS.get(language, [])
    
    # 1. Verify current question is valid in this language
    if request.question not in lang_questions:
        raise HTTPException(status_code=400, detail="Question is not part of this language set")
    
    current_index = lang_questions.index(request.question)
    
    # 2. Call Gemini model to evaluate the answer
    decision = gemini_service.evaluate_answer(request.question, request.answer)
    
    if decision == "Next":
        # Check if this interaction was already saved (to prevent duplicates if user resubmits)
        existing = db.query(InteractionModel).filter(
            InteractionModel.session_id == request.sessionId,
            InteractionModel.question == request.question
        ).first()

        if existing:
            existing.answer = request.answer
        else:
            interaction = InteractionModel(
                session_id=request.sessionId,
                language=language,
                question=request.question,
                answer=request.answer
            )
            db.add(interaction)
        
        db.commit()

        # Determine next question
        if current_index + 1 < len(lang_questions):
            next_question = lang_questions[current_index + 1]
            action = "Next"
        else:
            next_question = ""  # Completed all questions
            action = "Complete"
            logger.info(f"Session {request.sessionId} completed intake questions.")
    else:
        # Repeat the question
        action = "Repeat"
        next_question = request.question
        logger.info(f"Gemini requested repeat for question '{request.question}' in session {request.sessionId}")

    return SubmitAnswerResponse(action=action, question=next_question)


@app.post("/api/generate-summary", response_model=SummaryResponse)
def generate_summary(request: GenerateSummaryRequest, db: DBSession = Depends(get_db)):
    """
    Compiles the session's question-answer history and requests Gemini
    to build professional summaries in English, Hindi, and Marathi.
    """
    db_session = db.query(SessionModel).filter(SessionModel.id == request.sessionId).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Fetch all interaction history
    interactions = db.query(InteractionModel).filter(InteractionModel.session_id == request.sessionId).all()
    if not interactions:
        raise HTTPException(status_code=400, detail="No Q&A interactions found for this session")

    # Serialize history
    history = [{"question": item.question, "answer": item.answer} for item in interactions]
    
    # Call Gemini summary service
    summaries = gemini_service.generate_medical_summaries(history)
    
    # Save summaries to session
    db_session.english_summary = summaries["english_summary"]
    db_session.hindi_summary = summaries["hindi_summary"]
    db_session.marathi_summary = summaries["marathi_summary"]
    db.commit()
    
    logger.info(f"Generated and saved summaries for session {request.sessionId}")
    return SummaryResponse(
        english_summary=db_session.english_summary,
        hindi_summary=db_session.hindi_summary,
        marathi_summary=db_session.marathi_summary
    )


@app.get("/api/session/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    """
    Retrieves full details for a session, including histories and summaries.
    """
    db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return db_session


@app.get("/api/tts")
def get_tts(text: str = Query(..., description="Text to convert to speech"),
            lang: str = Query(..., description="Language: English, Hindi, Marathi")):
    """
    Generates a .wav or streaming audio file from the text using TTS and streams it to the client.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text query parameter cannot be empty")
        
    audio_bytes, mime_type = TTSService.generate_speech(text, lang)
    
    import io
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=mime_type)


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
