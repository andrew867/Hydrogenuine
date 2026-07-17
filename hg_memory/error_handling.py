#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error handling and resilience for memory engine.

Provides graceful degradation, retry logic, and recovery mechanisms.
"""

import sqlite3
import time
import shutil
from pathlib import Path
from typing import Optional, Callable, Any, Dict
from functools import wraps
import logging

from hg_memory.config import get_config

logger = logging.getLogger(__name__)


class MemoryEngineError(Exception):
    """Base exception for memory engine errors"""
    pass


class DatabaseCorruptionError(MemoryEngineError):
    """Database corruption detected"""
    pass


class RetryableError(MemoryEngineError):
    """Error that can be retried"""
    pass


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (RetryableError, sqlite3.OperationalError)
):
    """
    Decorator for retrying operations on transient failures.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")

            raise last_exception

        return wrapper
    return decorator


def graceful_fallback(file_operation: Callable):
    """
    Compatibility decorator that no longer falls back to files.

    File-backed fallback is retired; this now behaves like a pass-through
    wrapper that preserves the call signature for older imports while letting
    the database failure surface to the caller.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (DatabaseCorruptionError, sqlite3.DatabaseError) as e:
                logger.error(f"Database error in {func.__name__}: {e}. File fallback is retired.")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise

        return wrapper
    return decorator


def check_database_integrity(database_path: Path) -> bool:
    """
    Check database integrity.

    Args:
        database_path: Path to database file

    Returns:
        True if database is intact, False otherwise
    """
    if not database_path.exists():
        return False

    try:
        conn = sqlite3.connect(str(database_path))
        conn.execute("PRAGMA integrity_check")
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False


def backup_database(database_path: Path, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Create backup of database.

    Args:
        database_path: Path to database file
        backup_dir: Directory for backups (defaults to database directory)

    Returns:
        Path to backup file, or None if backup failed
    """
    if not database_path.exists():
        return None

    if backup_dir is None:
        backup_dir = database_path.parent / "backups"

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    backup_path = backup_dir / f"{database_path.stem}_{timestamp}.db.backup"

    try:
        shutil.copy2(database_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return None


def restore_database(backup_path: Path, target_path: Path) -> bool:
    """
    Restore database from backup.

    Args:
        backup_path: Path to backup file
        target_path: Path to restore to

    Returns:
        True if restore successful, False otherwise
    """
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        return False

    try:
        # Create backup of current database if it exists
        if target_path.exists():
            backup_database(target_path)

        shutil.copy2(backup_path, target_path)
        logger.info(f"Database restored from {backup_path} to {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore database: {e}")
        return False


def recover_from_corruption(database_path: Path) -> bool:
    """
    Attempt to recover from database corruption.

    Args:
        database_path: Path to corrupted database

    Returns:
        True if recovery successful, False otherwise
    """
    logger.warning(f"Attempting to recover corrupted database: {database_path}")

    # Try to find latest backup
    backup_dir = database_path.parent / "backups"
    if backup_dir.exists():
        backups = sorted(backup_dir.glob(f"{database_path.stem}_*.db.backup"), reverse=True)
        if backups:
            logger.info(f"Found {len(backups)} backups, restoring latest: {backups[0]}")
            return restore_database(backups[0], database_path)

    # If no backup, try to dump and recreate
    try:
        logger.info("No backup found, attempting to dump and recreate database")
        dump_path = database_path.with_suffix('.db.dump')

        # Try to dump what we can
        conn = sqlite3.connect(str(database_path))
        with open(dump_path, 'w', encoding='utf-8') as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        conn.close()

        # Remove corrupted database
        database_path.unlink()

        # Recreate from dump
        conn = sqlite3.connect(str(database_path))
        with open(dump_path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.close()

        dump_path.unlink()
        logger.info("Database recovered from dump")
        return True
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return False


class ConnectionPool:
    """Simple connection pool for SQLite databases"""

    def __init__(self, database_path: Path, max_connections: int = 5):
        """
        Initialize connection pool.

        Args:
            database_path: Path to database file
            max_connections: Maximum number of connections in pool
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self.connections = []
        self.in_use = set()

    def get_connection(self):
        """Get a connection from the pool"""
        # Try to reuse existing connection
        for conn in self.connections:
            if id(conn) not in self.in_use:
                self.in_use.add(id(conn))
                return conn

        # Create new connection if under limit
        if len(self.connections) < self.max_connections:
            conn = sqlite3.connect(str(self.database_path))
            conn.execute("PRAGMA encoding = 'UTF-8'")
            self.connections.append(conn)
            self.in_use.add(id(conn))
            return conn

        # Wait for connection to become available (simple implementation)
        # In production, use proper queue/semaphore
        time.sleep(0.1)
        return self.get_connection()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        self.in_use.discard(id(conn))

    def close_all(self):
        """Close all connections in pool"""
        for conn in self.connections:
            try:
                conn.close()
            except Exception:
                pass
        self.connections.clear()
        self.in_use.clear()


def atomic_write(database_path: Path, operation: Callable) -> bool:
    """
    Execute operation atomically (with transaction).

    Args:
        database_path: Path to database file
        operation: Function that takes a connection and performs operations

    Returns:
        True if operation successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(str(database_path))
        conn.execute("BEGIN TRANSACTION")

        operation(conn)

        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Atomic write failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
