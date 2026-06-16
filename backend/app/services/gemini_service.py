"""
Gemini API service with retry logic and connection pooling.
Handles answer validation and medical summary generation.
"""
import json
import logging
import asyncio
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config import GEMINI_API_KEY, GEMINI_TIMEOUT_S, GEMINI_MAX_RETRIES, GEMINI_RETRY_DELAY_MS
from app.retry.decorators import retry_with_backoff

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for Gemini API interactions with built-in retry logic."""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.api_key = GEMINI_API_KEY
        self._lock = asyncio.Lock()
        
        if self.api_key:
            try:
                # Initialize the Google GenAI client with connection pooling
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini API client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}. Running in MOCK mode.")
                self.client = None
        else:
            self.client = None
            logger.warning(
                "GEMINI_API_KEY is not set in backend/.env. Running Gemini Service in MOCK mode."
            )
        
        self._initialized = True
    
    @retry_with_backoff(
        max_retries=GEMINI_MAX_RETRIES,
        initial_delay_ms=GEMINI_RETRY_DELAY_MS,
        max_delay_ms=5000,
        backoff_factor=2.0,
        jitter=True,
        exceptions=(APIError, asyncio.TimeoutError, Exception)
    )
    async def evaluate_answer(self, question: str, answer: str) -> str:
        """
        Determines whether the user's answer is clear/valid ("Next")
        or if the question should be repeated.
        Async version with retry logic.
        """
        # If API key is missing or blank, use mock logic
        if not self.client:
            logger.debug("Gemini Service in Mock Mode: Evaluating answer.")
            return self._evaluate_answer_mock(question, answer)
        
        prompt = f"""
Analyze the user's answer to the given medical intake question.
Question: "{question}"
User's Answer: "{answer}"

Determine if the answer is clear, valid, and addresses the question (even if negative or brief).
- If the answer is valid (e.g., "Yes", "No", "I feel sick", "Since yesterday", etc.), output ONLY the word "Next".
- If the answer is unclear, empty, gibberish, indicates they did not hear or understand, or asks to repeat, output the EXACT question: "{question}".

STRICT RULES:
- Output ONLY the word "Next" OR the exact question.
- No punctuation, no markdown, no explanations.
"""
        
        try:
            # Run in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            max_output_tokens=50
                        )
                    )
                ),
                timeout=GEMINI_TIMEOUT_S
            )
            
            result = response.text.strip()
            logger.debug(f"Gemini Decision: '{result}' for Q: '{question[:50]}...'")
            
            # Sanitization: trim quotes if Gemini added any
            result_cleaned = result.replace('"', '').replace("'", "").strip()
            
            # Strict validation
            if result_cleaned.lower() == "next":
                return "Next"
            
            # If it's not "Next", return the original question to repeat
            return question
            
        except asyncio.TimeoutError:
            logger.error(f"Gemini API timeout after {GEMINI_TIMEOUT_S}s")
            raise
        except Exception as e:
            logger.error(f"Error calling Gemini for answer evaluation: {e}")
            raise
    
    @retry_with_backoff(
        max_retries=GEMINI_MAX_RETRIES,
        initial_delay_ms=GEMINI_RETRY_DELAY_MS,
        max_delay_ms=5000,
        backoff_factor=2.0,
        jitter=True,
        exceptions=(APIError, asyncio.TimeoutError, Exception)
    )
    async def generate_medical_summaries(self, history: list) -> dict:
        """
        Generates clinical summaries in English, Hindi, and Marathi based on Q&A history.
        Async version with retry logic.
        """
        history_str = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in history])

        if not self.client:
            logger.debug("Gemini Service in Mock Mode: Generating summaries.")
            return self._generate_medical_summaries_mock(history)

        prompt = f"""
You are a medical scribe. Summarize the patient's OPD intake pre-consultation responses.
Generate a concise, professional medical summary for the doctor.
Include symptoms, status, and notable positives/negatives.

Here is the Q&A history:
{history_str}

Generate the summary in English, Hindi, and Marathi.
Return a JSON object matching this exact structure:
{{
  "english_summary": "Clinical summary in English...",
  "hindi_summary": "Clinical summary in Hindi (written in Devanagari script)...",
  "marathi_summary": "Clinical summary in Marathi (written in Devanagari script)..."
}}
"""

        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                ),
                timeout=GEMINI_TIMEOUT_S
            )
            
            # Parse the JSON response
            data = json.loads(response.text)
            return {
                "english_summary": data.get("english_summary", "No English summary generated."),
                "hindi_summary": data.get("hindi_summary", "कोई हिंदी सारांश उपलब्ध नहीं है।"),
                "marathi_summary": data.get("marathi_summary", "कोणताही मराठी सारांश उपलब्ध नाही.")
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Gemini summary generation timeout after {GEMINI_TIMEOUT_S}s")
            raise
        except Exception as e:
            logger.error(f"Error calling Gemini for summary generation: {e}")
            raise
    
    # ============ MOCK IMPLEMENTATIONS ============
    @staticmethod
    def _evaluate_answer_mock(question: str, answer: str) -> str:
        """Mock answer evaluation."""
        sanitized_ans = answer.strip().lower()
        confusion_keywords = [
            "repeat", "clear", "dont understand", "don't understand",
            "dont know", "don't know", "idk", "not sure",
            "can't hear", "cant hear", "say again", "again",
            "what", "huh", "unsure"
        ]
        has_confusion = any(k in sanitized_ans for k in confusion_keywords)
        alnum_count = sum(1 for c in sanitized_ans if c.isalnum())
        
        if not sanitized_ans or has_confusion or alnum_count < 2:
            return question
        return "Next"
    
    @staticmethod
    def _generate_medical_summaries_mock(history: list) -> dict:
        """Mock summary generation."""
        summary_en = f"Patient pre-consultation OPD history collection complete. Key points: " + ", ".join([f"{h['question']}: {h['answer']}" for h in history[:3]])
        summary_hi = f"मरीज का ओपीडी इतिहास पूरा: " + ", ".join([f"{h['question']}: {h['answer']}" for h in history[:3]])
        summary_mr = f"रुग्णाचा ओपीडी इतिहास पूर्ण: " + ", ".join([f"{h['question']}: {h['answer']}" for h in history[:3]])
        
        return {
            "english_summary": summary_en,
            "hindi_summary": summary_hi,
            "marathi_summary": summary_mr
        }


# Singleton instance
gemini_service = GeminiService()

