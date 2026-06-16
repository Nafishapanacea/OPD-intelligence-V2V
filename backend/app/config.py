import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============ API KEYS ============
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ============ DATABASE ============
# IMPORTANT: Switch from SQLite to PostgreSQL for production
# Format: postgresql+asyncpg://user:password@localhost:5432/opd_db
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/opd_assistant"
)

# PostgreSQL connection pool settings
DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "10"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "20"))
DB_POOL_TIMEOUT_S = int(os.getenv("DB_POOL_TIMEOUT_S", "30"))
DB_COMMAND_TIMEOUT_S = int(os.getenv("DB_COMMAND_TIMEOUT_S", "10"))

# ============ REDIS ============
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))

# ============ TTS WORKERS ============
# Max concurrent OmniVoice inference tasks (limited by VRAM: 24GB ÷ 4.9GB ≈ 5)
TTS_MAX_WORKERS = int(os.getenv("TTS_MAX_WORKERS", "5"))

# TTS inference timeout (seconds)
TTS_WORKER_TIMEOUT_S = int(os.getenv("TTS_WORKER_TIMEOUT_S", "30"))

# TTS queue max depth (tasks rejected if exceeded)
TTS_QUEUE_MAX_DEPTH = int(os.getenv("TTS_QUEUE_MAX_DEPTH", "1000"))

# ============ GEMINI API ============
# Timeout for Gemini API calls (seconds)
GEMINI_TIMEOUT_S = int(os.getenv("GEMINI_TIMEOUT_S", "15"))

# Retry settings for Gemini API
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
GEMINI_RETRY_DELAY_MS = int(os.getenv("GEMINI_RETRY_DELAY_MS", "100"))

# ============ FASTAPI ============
PORT = int(os.getenv("PORT", "8002"))
HOST = os.getenv("HOST", "0.0.0.0")
WORKERS = int(os.getenv("WORKERS", "1"))  # Single worker for async
RELOAD = os.getenv("RELOAD", "False").lower() == "true"

# ============ CORS ============
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# ============ LOGGING ============
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
