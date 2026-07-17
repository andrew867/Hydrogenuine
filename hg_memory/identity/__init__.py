#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identity Graph System

Tracks and analyzes agent identity (SOUL/HEART/IDENTITY) evolution over time.
"""

__version__ = "0.1.0"

# Import core classes
from .identity_search import IdentitySearch
from .identity_graph_db import IdentityGraphDatabase
from .identity_recorder import IdentityRecorder
from .identity_extractor import IdentityExtractor
from .identity_analytics import IdentityAnalytics
from .identity_health import health_check as get_identity_health
from .identity_cache import IdentityCache
from .identity_error_handler import IdentityErrorHandler, get_error_handler as get_identity_error_handler
from .config import get_identity_graph_db_path

# Import from agent_task_integration if available
try:
    from hg_memory.agent.agent_task_integration import search_agent_identity
except ImportError:
    search_agent_identity = None

__all__ = [
    'IdentitySearch',
    'IdentityGraphDatabase',
    'IdentityRecorder',
    'IdentityExtractor',
    'IdentityAnalytics',
    'IdentityCache',
    'IdentityErrorHandler',
    'get_identity_graph_db_path',
    'get_identity_health',
    'get_identity_error_handler',
]

if search_agent_identity:
    __all__.append('search_agent_identity')
