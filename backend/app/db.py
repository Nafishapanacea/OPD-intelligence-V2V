"""Database configuration and connection management."""
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import DATABASE_URL, DB_POOL_MIN, DB_POOL_MAX, DB_POOL_TIMEOUT_S, DB_COMMAND_TIMEOUT_S

logger = logging.getLogger(__name__)

# Declarative base for all models
Base = declarative_base()

# ============ ASYNC POSTGRESQL SUPPORT ============
# Create async engine with asyncpg for production use

if DATABASE_URL.startswith("sqlite"):
    if DATABASE_URL.startswith("sqlite+aiosqlite"):
        async_db_url = DATABASE_URL
    else:
        # Convert sqlite:// to sqlite+aiosqlite:// for async support
        async_db_url = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
    logger.info(f"Database: Initializing async SQLite engine with URL: {async_db_url}")
    async_engine = create_async_engine(
        async_db_url,
        echo=True,
    )
else:
    logger.info("Database: Initializing async PostgreSQL engine")
    async_engine = create_async_engine(
        DATABASE_URL,
        pool_size=DB_POOL_MIN,
        max_overflow=DB_POOL_MAX - DB_POOL_MIN,
        pool_timeout=DB_POOL_TIMEOUT_S,
        echo=True,
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ============ LEGACY SYNC SUPPORT (for migration) ============
# Keep synchronous engine for backward compatibility during migration
# This will use standard psycopg2 driver instead of asyncpg
if "sqlite" in DATABASE_URL:
    # Convert sqlite+aiosqlite:// back to sqlite:// for sync engine compatibility
    sync_db_url = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://", 1)
    logger.info(f"Database: Initializing sync SQLite engine with URL: {sync_db_url}")
    # SQLite for development/testing
    connect_args = {"check_same_thread": False}
    sync_engine = create_engine(sync_db_url, connect_args=connect_args)
else:
    # PostgreSQL synchronous for backward compatibility
    # Convert asyncpg URL to psycopg2 URL
    sync_db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    sync_engine = create_engine(
        sync_db_url,
        pool_size=DB_POOL_MIN,
        max_overflow=DB_POOL_MAX - DB_POOL_MIN,
        pool_timeout=DB_POOL_TIMEOUT_S,
        pool_pre_ping=True,
        pool_recycle=3600
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# ============ DEPENDENCY INJECTION ============
# For async FastAPI routes
async def get_async_db():
    """Async database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# For sync FastAPI routes (legacy)
def get_db():
    """Sync database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ INITIALIZATION ============
async def init_async_db():
    """Initialize async database (create tables)."""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Async database initialized successfully")
    except Exception as e:
        # Ignore operational errors when tables are already created (fixes multi-worker startup race conditions in SQLite)
        if "already exists" in str(e):
            logger.info("Async database tables already created by another worker process, skipping creation.")
        else:
            logger.error(f"Failed to initialize async database: {e}")
            raise

def init_sync_db():
    """Initialize sync database (create tables)."""
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Sync database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize sync database: {e}")
        raise

