#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error handling and graceful degradation for identity graph system.
"""

import logging
from typing import Optional, Callable, Any, List
from functools import wraps
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class IdentityErrorHandler:
    """Error handler for identity graph operations"""
    
    def __init__(self, fallback_enabled: bool = True):
        """
        Initialize error handler.
        
        Args:
            fallback_enabled: Compatibility flag retained for older callers.
        """
        self.fallback_enabled = fallback_enabled
    
    def handle_database_error(self, error: Exception, operation: str) -> Optional[Any]:
        """
        Handle database errors with graceful degradation.
        
        Args:
            error: Exception that occurred
            operation: Description of operation that failed
            
        Returns:
            Fallback result or None
        """
        if isinstance(error, sqlite3.OperationalError):
            if "database is locked" in str(error).lower():
                logger.warning(f"Database locked during {operation}, retrying may help")
                return None
            elif "no such table" in str(error).lower():
                logger.error(f"Database schema error during {operation}: {error}")
                return None
            elif "database disk image is malformed" in str(error).lower():
                logger.error(f"Database corruption detected during {operation}: {error}")
                return None
            else:
                logger.warning(f"Database operational error during {operation}: {error}")
                return None
        elif isinstance(error, sqlite3.IntegrityError):
            logger.warning(f"Database integrity error during {operation}: {error}")
            return None
        else:
            logger.error(f"Unexpected error during {operation}: {error}")
            return None
    
    def retry_on_failure(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        retryable_errors: Optional[List[type]] = None
    ):
        """
        Decorator to retry operations on failure.
        
        Args:
            max_retries: Maximum number of retries
            retry_delay: Delay between retries (seconds)
            retryable_errors: List of exception types to retry on
        """
        if retryable_errors is None:
            retryable_errors = [sqlite3.OperationalError]
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_error = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except tuple(retryable_errors) as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                            logger.debug(f"Retrying {func.__name__} (attempt {attempt + 1}/{max_retries})")
                        else:
                            logger.warning(f"Failed {func.__name__} after {max_retries} attempts: {e}")
                    except Exception as e:
                        # Non-retryable error
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                
                # All retries failed
                if last_error:
                    raise last_error
                return None
            
            return wrapper
        return decorator
    
    def fallback_to_files(self, operation: str) -> Callable:
        """
        Compatibility decorator that no longer falls back to files.
        
        Args:
            operation: Description of operation for logging
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Database operation failed for {operation}; file fallback is retired: {e}")
                    raise
            
            return wrapper
        return decorator


# Global error handler instance
_error_handler = IdentityErrorHandler()


def get_error_handler() -> IdentityErrorHandler:
    """Get global error handler instance"""
    return _error_handler
