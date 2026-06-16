"""
Async PostgreSQL connection pooling using asyncpg.
Replaces synchronous SQLAlchemy engine for production scalability.
"""
import logging
from typing import Optional
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class PostgresAsyncPool:
    """Async PostgreSQL connection pool manager."""
    
    _engine = None
    _session_factory = None
    _pool = None
    
    @classmethod
    async def initialize(
        cls,
        database_url: str,
        min_connections: int = 10,
        max_connections: int = 20,
        timeout_s: int = 30,
        command_timeout_s: int = 10
    ):
        """Initialize async PostgreSQL engine and connection pool."""
        if cls._engine is not None:
            logger.warning("PostgreSQL pool already initialized")
            return
        
        try:
            # Create async engine with asyncpg driver
            cls._engine = create_async_engine(
                database_url,
                echo=False,
                pool_size=min_connections,
                max_overflow=max_connections - min_connections,
                pool_timeout=timeout_s,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                connect_args={
                    "timeout": timeout_s,
                    "command_timeout": command_timeout_s,
                    "server_settings": {
                        "jit": "off"  # Disable JIT compilation for consistency
                    }
                }
            )
            
            # Create async session factory
            cls._session_factory = async_sessionmaker(
                cls._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Verify connection
            async with cls._engine.begin() as conn:
                await conn.exec_driver_sql("SELECT 1")
            
            logger.info(
                f"PostgreSQL pool initialized: min={min_connections}, max={max_connections}, "
                f"URL={database_url.split('@')[1] if '@' in database_url else database_url[:30]}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise
    
    @classmethod
    async def get_session(cls) -> AsyncSession:
        """Get a new async database session from pool."""
        if cls._session_factory is None:
            raise RuntimeError("PostgreSQL pool not initialized. Call initialize() first.")
        
        return cls._session_factory()
    
    @classmethod
    async def execute_query(cls, query):
        """Execute a query and return results (convenience method)."""
        async with await cls.get_session() as session:
            result = await session.execute(query)
            return result.fetchall()
    
    @classmethod
    async def close(cls):
        """Close all connections in pool."""
        if cls._engine:
            await cls._engine.dispose()
            logger.info("PostgreSQL pool closed")
            cls._engine = None
            cls._session_factory = None
    
    @classmethod
    async def health_check(cls) -> bool:
        """Check pool health."""
        try:
            async with await cls.get_session() as session:
                await session.exec_driver_sql("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    @classmethod
    async def get_pool_stats(cls) -> dict:
        """Get connection pool statistics."""
        if cls._engine is None or cls._engine.pool is None:
            return {}
        
        pool = cls._engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow()
        }


# Context manager for database sessions
class get_async_db:
    """Dependency for FastAPI async endpoints."""
    
    @staticmethod
    async def __call__():
        async with await PostgresAsyncPool.get_session() as session:
            yield session


# Helper for creating tables (migrate on startup)
async def create_all_tables():
    """Create all tables from SQLAlchemy models."""
    from app.database import Base
    
    engine = None
    try:
        engine = create_async_engine(
            "postgresql+asyncpg://user:password@localhost/opd_db"  # Placeholder
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
    finally:
        if engine:
            await engine.dispose()
