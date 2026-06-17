"""Standalone TTS worker process that consumes tasks from Redis queue."""
import asyncio
import logging
import sys
import os
import json
from asyncio import Semaphore
from typing import Optional
import signal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.queue.redis_client import RedisClient
from app.queue.task_schemas import TTSTaskSchema, TTSResultSchema
from app.services.tts_service import TTSService
from app.retry.decorators import retry_with_backoff
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB, TTS_WORKER_TIMEOUT_S
from datetime import datetime
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TTS_WORKER - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TTSWorkerPool:
    """Manages pool of TTS worker tasks."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.running = False
        self.tasks_processed = 0
        self.tasks_failed = 0
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            await RedisClient.initialize(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                max_connections=10
            )
            logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def process_task(self, task_dict: dict) -> bool:
        """Process a single TTS task with semaphore protection."""
        async with self.semaphore:
            try:
                task = TTSTaskSchema(**task_dict)
                logger.info(f"Processing task {task.task_id} (attempt {task.attempt}/{task.max_retries + 1})")
                
                # Generate speech
                start_time = datetime.utcnow()
                try:
                    audio_bytes, mime_type = await self._generate_speech_with_timeout(
                        task.text, task.language, timeout_s=TTS_WORKER_TIMEOUT_S
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Task {task.task_id} timed out after {TTS_WORKER_TIMEOUT_S}s")
                    if task.attempt < task.max_retries:
                        # Requeue for retry
                        task.attempt += 1
                        await RedisClient.push_task("tts_tasks", task.model_dump(mode='json'))
                        return False
                    else:
                        # Max retries exceeded
                        result = TTSResultSchema(
                            task_id=task.task_id,
                            status="failed",
                            error=f"Timeout after {TTS_WORKER_TIMEOUT_S}s",
                            processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                            created_at=datetime.utcnow()
                        )
                        await RedisClient.set_result(f"tts_result:{task.task_id}", json.loads(result.model_dump_json()))
                        return False
                
                processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Store result
                import base64
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                
                result = TTSResultSchema(
                    task_id=task.task_id,
                    status="success",
                    audio_base64=audio_base64,
                    mime_type=mime_type,
                    processing_time_ms=processing_time_ms,
                    created_at=datetime.utcnow(),
                    attempt=task.attempt
                )
                
                await RedisClient.set_result(f"tts_result:{task.task_id}", json.loads(result.model_dump_json()))
                logger.info(f"Task {task.task_id} completed in {processing_time_ms}ms")
                
                self.tasks_processed += 1
                return True
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                self.tasks_failed += 1
                return False
    
    @retry_with_backoff(max_retries=2, initial_delay_ms=50)
    async def _generate_speech_with_timeout(self, text: str, language: str, 
                                           timeout_s: int) -> tuple:
        """Generate speech with timeout and retry."""
        try:
            # Run TTS in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            audio_bytes, mime_type = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: TTSService.generate_speech(text, language)),
                timeout=timeout_s
            )
            return audio_bytes, mime_type
        except asyncio.TimeoutError:
            raise
    
    async def run(self, poll_interval_s: int = 1):
        """Main worker loop - consume tasks from Redis queue."""
        self.running = True
        logger.info(f"TTS Worker Pool started (max_concurrent={self.max_concurrent})")
        
        # Log initial queue depth
        try:
            initial_depth = await RedisClient.peek_queue_depth("tts_tasks")
            logger.info(f"Initial queue depth: {initial_depth}")
        except Exception as e:
            logger.warning(f"Could not check initial queue depth: {e}")
        
        try:
            while self.running:
                try:
                    # Pop task from queue (blocking with timeout)
                    logger.debug("Waiting for task from Redis queue 'tts_tasks'...")
                    task_dict = await RedisClient.pop_task("tts_tasks", timeout=poll_interval_s)
                    
                    if task_dict:
                        task_id = task_dict.get('task_id', 'unknown')
                        logger.info(f"📥 Popped task {task_id} from queue")
                        # Process task (semaphore-limited)
                        success = await self.process_task(task_dict)
                        logger.info(f"{'✅' if success else '❌'} Task {task_id} result: {'success' if success else 'failed'}")
                    # Only log queue depth every ~30 seconds to reduce noise
                
                except Exception as e:
                    logger.error(f"Worker loop error: {e}", exc_info=True)
                    await asyncio.sleep(poll_interval_s)
        
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker crashed: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info(f"Shutting down worker (processed={self.tasks_processed}, failed={self.tasks_failed})")
        self.running = False
        await RedisClient.close()
    
    async def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "max_concurrent": self.max_concurrent,
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "queue_depth": await RedisClient.peek_queue_depth("tts_tasks")
        }


async def run_worker(worker_id: int = 1, max_concurrent: int = 5):
    """Run a TTS worker instance."""
    logger.info(f"Starting TTS Worker #{worker_id}")
    
    pool = TTSWorkerPool(max_concurrent=max_concurrent)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(pool.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await pool.initialize()
    await pool.run()


if __name__ == "__main__":
    # Run worker with configurable concurrency
    worker_id = int(os.getenv("WORKER_ID", "1"))
    max_concurrent = int(os.getenv("MAX_CONCURRENT", "1"))
    
    logger.info(f"Worker configuration: ID={worker_id}, MAX_CONCURRENT={max_concurrent}")
    
    asyncio.run(run_worker(worker_id=worker_id, max_concurrent=max_concurrent))
