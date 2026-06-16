"""Retry decorators with exponential backoff for resilient API calls."""
import logging
import asyncio
from functools import wraps
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay_ms: int = 100,
    max_delay_ms: int = 5000,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Max number of retry attempts (not including initial)
        initial_delay_ms: Initial delay in milliseconds
        max_delay_ms: Maximum delay between retries
        backoff_factor: Multiplier for delay (e.g., 2.0 for exponential)
        jitter: Add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @retry_with_backoff(max_retries=3, initial_delay_ms=100)
        async def call_gemini_api(prompt: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay_ms
            last_exception = None
            
            # Initial attempt + retries
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(f"{func.__name__} attempt {attempt + 1}/{max_retries + 1}")
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded after {attempt} retries")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate next delay with jitter
                        next_delay = min(delay * backoff_factor, max_delay_ms)
                        jitter_ms = (next_delay * 0.1) if jitter else 0
                        
                        import random
                        actual_delay_ms = next_delay + random.uniform(-jitter_ms, jitter_ms)
                        actual_delay_ms = max(0, actual_delay_ms)  # No negative delays
                        
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}): {str(e)[:100]}. "
                            f"Retrying in {actual_delay_ms:.0f}ms..."
                        )
                        await asyncio.sleep(actual_delay_ms / 1000.0)
                        delay = next_delay
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {str(e)[:100]}"
                        )
            
            # All retries exhausted
            raise last_exception or Exception(f"{func.__name__} failed after {max_retries + 1} attempts")
        
        # Handle sync functions too (if needed)
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay_ms
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(f"{func.__name__} attempt {attempt + 1}/{max_retries + 1}")
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded after {attempt} retries")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        next_delay = min(delay * backoff_factor, max_delay_ms)
                        jitter_ms = (next_delay * 0.1) if jitter else 0
                        
                        import random
                        actual_delay_ms = next_delay + random.uniform(-jitter_ms, jitter_ms)
                        actual_delay_ms = max(0, actual_delay_ms)
                        
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}): {str(e)[:100]}. "
                            f"Retrying in {actual_delay_ms:.0f}ms..."
                        )
                        import time
                        time.sleep(actual_delay_ms / 1000.0)
                        delay = next_delay
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {str(e)[:100]}"
                        )
            
            raise last_exception or Exception(f"{func.__name__} failed after {max_retries + 1} attempts")
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CircuitBreaker:
    """Circuit breaker for failing services (e.g., Gemini API rate limits)."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_s: int = 60,
        name: str = "CircuitBreaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            # Check if recovery timeout passed
            import time
            if time.time() - self.last_failure_time > self.recovery_timeout_s:
                logger.info(f"{self.name} circuit breaker: moving to half-open state")
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen(f"{self.name} circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset on half-open
            if self.state == "half-open":
                logger.info(f"{self.name} circuit breaker: recovered, moving to closed state")
                self.state = "closed"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            
            import time
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"{self.name} circuit breaker: threshold reached ({self.failure_count}), "
                    f"opening circuit for {self.recovery_timeout_s}s"
                )
                self.state = "open"
            
            raise


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout_s: int = 60,
    name: str = "CircuitBreaker"
):
    """Decorator for circuit breaker pattern."""
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout_s=recovery_timeout_s,
        name=name
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            return breaker.call(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
