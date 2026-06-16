"""
Async Redis client for task queueing and caching.
Handles connection pooling, task serialization, and result retrieval.
"""
import json
import logging
import asyncio
from typing import Optional, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Singleton async Redis client with connection pooling."""
    
    _instance: Optional['RedisClient'] = None
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def initialize(cls, host: str = "localhost", port: int = 6379, 
                        db: int = 0, max_connections: int = 50):
        """Initialize Redis connection pool."""
        if cls._pool is None:
            try:
                cls._pool = redis.ConnectionPool.from_url(
                    f"redis://{host}:{port}/{db}",
                    max_connections=max_connections,
                    decode_responses=False  # We handle encoding ourselves
                )
                cls._client = redis.Redis(connection_pool=cls._pool)
                # Verify connection
                await cls._client.ping()
                logger.info(f"Redis connected: {host}:{port} db={db}")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                raise
    
    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get Redis client instance, initializing if needed."""
        if cls._client is None:
            await cls.initialize()
        return cls._client
    
    @classmethod
    async def close(cls):
        """Close Redis connections."""
        if cls._client:
            await cls._client.close()
            cls._client = None
        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None
    
    @staticmethod
    async def push_task(queue_name: str, task: Dict[str, Any]) -> str:
        """Push a task to a queue (FIFO)."""
        client = await RedisClient.get_client()
        task_json = json.dumps(task)
        try:
            # Push to queue with auto-expiry (24 hours)
            await client.rpush(queue_name, task_json)
            await client.expire(queue_name, 86400)
            logger.debug(f"Task pushed to {queue_name}: {task.get('task_id', 'unknown')}")
            return task.get('task_id', '')
        except Exception as e:
            logger.error(f"Failed to push task to {queue_name}: {e}")
            raise
    
    @staticmethod
    async def pop_task(queue_name: str, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """Pop a task from a queue (blocking with timeout)."""
        client = await RedisClient.get_client()
        try:
            task_json = await client.blpop(queue_name, timeout=timeout)
            if task_json:
                return json.loads(task_json[1])
            return None
        except Exception as e:
            logger.error(f"Failed to pop task from {queue_name}: {e}")
            return None
    
    @staticmethod
    async def peek_queue_depth(queue_name: str) -> int:
        """Get number of pending tasks in queue."""
        client = await RedisClient.get_client()
        try:
            depth = await client.llen(queue_name)
            return depth
        except Exception as e:
            logger.error(f"Failed to get queue depth for {queue_name}: {e}")
            return 0
    
    @staticmethod
    async def set_result(result_key: str, result: Dict[str, Any], ttl: int = 3600) -> bool:
        """Store task result with TTL (default 1 hour)."""
        client = await RedisClient.get_client()
        try:
            result_json = json.dumps(result)
            await client.setex(result_key, ttl, result_json)
            logger.debug(f"Result stored: {result_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store result {result_key}: {e}")
            return False
    
    @staticmethod
    async def get_result(result_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve task result from cache."""
        client = await RedisClient.get_client()
        try:
            result_json = await client.get(result_key)
            if result_json:
                return json.loads(result_json)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve result {result_key}: {e}")
            return None
    
    @staticmethod
    async def delete_result(result_key: str) -> bool:
        """Delete a result from cache."""
        client = await RedisClient.get_client()
        try:
            await client.delete(result_key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete result {result_key}: {e}")
            return False
    
    @staticmethod
    async def increment_counter(counter_key: str) -> int:
        """Increment a counter (for metrics)."""
        client = await RedisClient.get_client()
        try:
            return await client.incr(counter_key)
        except Exception as e:
            logger.error(f"Failed to increment counter {counter_key}: {e}")
            return 0
    
    @staticmethod
    async def get_counter(counter_key: str) -> int:
        """Get counter value."""
        client = await RedisClient.get_client()
        try:
            val = await client.get(counter_key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"Failed to get counter {counter_key}: {e}")
            return 0
    
    @staticmethod
    async def health_check() -> bool:
        """Check Redis connection health."""
        try:
            client = await RedisClient.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
