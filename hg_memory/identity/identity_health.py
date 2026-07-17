#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health check and monitoring for identity graph system.
"""

from typing import Dict, Optional
from pathlib import Path
import sqlite3

from .identity_graph_db import IdentityGraphDatabase
from .config import get_identity_graph_db_path


def health_check(agent_id: Optional[str] = None) -> Dict[str, any]:
    """
    Perform health check on identity graph database.
    
    Args:
        agent_id: Optional agent ID to check specific database
        
    Returns:
        Dictionary with health status and metrics
    """
    health = {
        'status': 'healthy',
        'database_exists': False,
        'database_accessible': False,
        'schema_version': 0,
        'entity_count': 0,
        'relation_count': 0,
        'version_count': 0,
        'pattern_count': 0,
        'errors': []
    }
    
    try:
        db_path = get_identity_graph_db_path(agent_id)
        health['database_exists'] = db_path.exists()
        
        if not health['database_exists']:
            health['status'] = 'degraded'
            health['errors'].append('Database file does not exist')
            return health
        
        # Try to open database
        try:
            db = IdentityGraphDatabase(str(db_path))
            health['database_accessible'] = True
            health['schema_version'] = db.get_schema_version()
            
            # Get counts
            conn = db._get_connection()
            try:
                # Entity count
                cursor = conn.execute("SELECT COUNT(*) FROM identity_entities WHERE deleted_at IS NULL")
                health['entity_count'] = cursor.fetchone()[0]
                
                # Relation count
                cursor = conn.execute("SELECT COUNT(*) FROM identity_relations")
                health['relation_count'] = cursor.fetchone()[0]
                
                # Version count
                cursor = conn.execute("SELECT COUNT(*) FROM identity_versions")
                health['version_count'] = cursor.fetchone()[0]
                
                # Pattern count
                cursor = conn.execute("SELECT COUNT(*) FROM identity_patterns")
                health['pattern_count'] = cursor.fetchone()[0]
            finally:
                conn.close()
            
        except sqlite3.Error as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f'Database error: {str(e)}')
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f'Unexpected error: {str(e)}')
            
    except Exception as e:
        health['status'] = 'unhealthy'
        health['errors'].append(f'Health check failed: {str(e)}')
    
    return health
