import json
import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        if self.api_key:
            # Initialize the Google GenAI client
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning(
                "GEMINI_API_KEY is not set in backend/.env. Running Gemini Service in MOCK mode."
            )

    def evaluate_answer(self, question: str, answer: str) -> str:
        """
        Determines whether the user's answer is clear/valid ("Next")
        or if the question should be repeated ("Repeat").
        """
        # If API key is missing or blank, use mock logic
        if not self.client:
            logger.info("Gemini Service in Mock Mode: Evaluating answer.")
            # Basic validation: if answer has at least one alphanumeric character, pass it.
            # If empty or asking to repeat, repeat the question.
            sanitized_ans = answer.strip().lower()
            if not sanitized_ans or "repeat" in sanitized_ans or "clear" in sanitized_ans or len(sanitized_ans) < 2:
                return question
            return "Next"

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
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=50
                )
            )
            result = response.text.strip()
            logger.info(f"Gemini Decision Output: '{result}' for question '{question}' and answer '{answer}'")
            
            # Sanitization of response: trim quotes if Gemini added any
            result_cleaned = result.replace('"', '').replace("'", "").strip()
            
            # Strict validation
            if result_cleaned.lower() == "next":
                return "Next"
            
            # If it's not "Next", return the original question to repeat
            return question
            
        except Exception as e:
            logger.error(f"Error calling Gemini for answer evaluation: {e}. Falling back to 'Next' if answer has content.")
            if len(answer.strip()) > 1:
                return "Next"
            return question

    def generate_medical_summaries(self, history: list) -> dict:
        """
        Generates clinical summaries in English, Hindi, and Marathi based on the session's Q&A history.
        history is a list of dicts: [{"question": str, "answer": str}]
        """
        history_str = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in history])

        if not self.client:
            logger.info("Gemini Service in Mock Mode: Generating summaries.")
            # Return basic mock summaries using the history
            summary_en = f"Patient pre-consultation OPD history collection complete. Key points reported: " + ", ".join([f"{h['question']}: {h['answer']}" for h in history])
            summary_hi = f"मरीज का ओपीडी इतिहास संग्रह पूरा हो गया है। विवरण: " + ", ".join([f"{h['question']}: {h['answer']}" for h in history])
            summary_mr = f"रुग्णाचा ओपीडी इतिहास संग्रह पूर्ण झाला आहे. तपशील: " + ", ".join([f"{h['question']}: {h['answer']}" for h in history])
            return {
                "english_summary": summary_en,
                "hindi_summary": summary_hi,
                "marathi_summary": summary_mr
            }

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
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # Parse the JSON response
            data = json.loads(response.text)
            return {
                "english_summary": data.get("english_summary", "No English summary generated."),
                "hindi_summary": data.get("hindi_summary", "कोई हिंदी सारांश उपलब्ध नहीं है।"),
                "marathi_summary": data.get("marathi_summary", "कोणताही मराठी सारांश उपलब्ध नाही.")
            }
            
        except Exception as e:
            logger.error(f"Error calling Gemini for summary generation: {e}")
            # Dynamic fallback
            return {
                "english_summary": f"Failed to generate summary via Gemini. Q&A History:\n{history_str}",
                "hindi_summary": f"जेमिनीद्वारे सारांश तयार करण्यात अयशस्वी. इतिहास:\n{history_str}",
                "marathi_summary": f"जेमिनीद्वारे सारांश तयार करण्यात अयशस्वी. इतिहास:\n{history_str}"
            }
