import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# OmniVoice API URL (optional fallback)
OMNIVOICE_API_URL = os.getenv("OMNIVOICE_API_URL", "")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./opd_assistant.db")

# Server settings
PORT = int(os.getenv("PORT", 8000))
