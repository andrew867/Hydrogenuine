#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identity recorder.

Records extracted identity components to identity graph database.
Integrates with persona version control for tracking changes.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from .identity_graph_db import IdentityGraphDatabase
from .identity_extractor import IdentityExtractor


class IdentityRecorder:
    """Record identity components to graph database"""
    
    def __init__(self, database: Optional[IdentityGraphDatabase] = None, agent_id: Optional[str] = None):
        """
        Initialize identity recorder.
        
        Args:
            database: IdentityGraphDatabase instance (creates new if None)
            agent_id: Optional agent ID
        """
        from .config import get_identity_graph_db_path
        
        if database is None:
            database_path = get_identity_graph_db_path(agent_id)
            database = IdentityGraphDatabase(str(database_path))
        
        self.database = database
        self.agent_id = agent_id
        self.extractor = IdentityExtractor()
    
    def record_persona_files(
        self,
        soul_path: Optional[Path] = None,
        heart_path: Optional[Path] = None,
        identity_path: Optional[Path] = None,
        platform: Optional[str] = None,
        persona_set: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Record identity components from persona files.
        
        Args:
            soul_path: Path to SOUL.md
            heart_path: Path to HEART.md
            identity_path: Path to IDENTITY.md
            platform: Optional platform identifier
            persona_set: Optional persona set identifier
        
        Returns:
            Dictionary with counts: entities, patterns, relationships, versions
        """
        # Extract components
        extraction_result = self.extractor.extract_from_files(
            soul_path=soul_path,
            heart_path=heart_path,
            identity_path=identity_path
        )
        
        entities = extraction_result.get('entities', [])
        patterns = extraction_result.get('patterns', [])
        relationships = extraction_result.get('relationships', [])
        
        # Record entities
        entity_count = 0
        for entity in entities:
            try:
                self.database.insert_entity(
                    entity_id=entity['entity_id'],
                    entity_type=entity['entity_type'],
                    content=entity['content'],
                    agent_id=self.agent_id,
                    platform=platform,
                    properties=entity.get('properties', {})
                )
                entity_count += 1
            except Exception as e:
                # Log error but continue
                print(f"Warning: Failed to insert entity {entity['entity_id']}: {e}")
        
        # Record patterns
        pattern_count = 0
        for pattern in patterns:
            try:
                pattern_id = pattern.get('pattern_id', f"pattern:{uuid.uuid4().hex[:8]}")
                self.database.insert_pattern(
                    pattern_id=pattern_id,
                    pattern_type=pattern['pattern_type'],
                    agent_id=self.agent_id,
                    platform=platform,
                    properties=pattern.get('properties', {})
                )
                pattern_count += 1
            except Exception as e:
                print(f"Warning: Failed to insert pattern {pattern.get('pattern_id')}: {e}")
        
        # Record relationships
        relationship_count = 0
        for relationship in relationships:
            try:
                self.database.insert_relation(
                    from_entity_id=relationship['from_entity_id'],
                    to_entity_id=relationship['to_entity_id'],
                    relation_type=relationship['relation_type']
                )
                relationship_count += 1
            except Exception as e:
                print(f"Warning: Failed to insert relationship: {e}")
        
        # Record versions
        version_count = 0
        timestamp = datetime.now().isoformat()
        
        for file_path, file_name in [
            (soul_path, "SOUL.md"),
            (heart_path, "HEART.md"),
            (identity_path, "IDENTITY.md")
        ]:
            if file_path and file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    version_id = f"version:{file_name}:{content_hash[:16]}"
                    
                    self.database.insert_version(
                        version_id=version_id,
                        persona_file=file_name,
                        content_hash=content_hash,
                        platform=platform,
                        persona_set=persona_set,
                        agent_id=self.agent_id,
                        timestamp=timestamp
                    )
                    version_count += 1
                except Exception as e:
                    print(f"Warning: Failed to record version for {file_name}: {e}")
        
        return {
            'entities': entity_count,
            'patterns': pattern_count,
            'relationships': relationship_count,
            'versions': version_count
        }
    
    def record_persona_update(
        self,
        persona_file: str,
        file_path: Path,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None,
        platform: Optional[str] = None,
        persona_set: Optional[str] = None
    ) -> bool:
        """
        Record a persona file update with diff tracking.
        
        Args:
            persona_file: Persona file name (SOUL.md, HEART.md, IDENTITY.md)
            file_path: Path to persona file
            before_content: Content before update (optional)
            after_content: Content after update (optional)
            platform: Optional platform identifier
            persona_set: Optional persona set identifier
        
        Returns:
            True if successful, False otherwise
        """
        if not file_path.exists():
            return False
        
        # Read current content if not provided
        if after_content is None:
            after_content = file_path.read_text(encoding='utf-8')
        
        content_hash = hashlib.sha256(after_content.encode('utf-8')).hexdigest()
        version_id = f"version:{persona_file}:{content_hash[:16]}"
        timestamp = datetime.now().isoformat()
        
        try:
            # Record version
            self.database.insert_version(
                version_id=version_id,
                persona_file=persona_file,
                content_hash=content_hash,
                platform=platform,
                persona_set=persona_set,
                agent_id=self.agent_id,
                timestamp=timestamp,
                diff_before=before_content,
                diff_after=after_content
            )
            
            # Re-extract and record entities
            if persona_file == "SOUL.md":
                self.record_persona_files(soul_path=file_path, platform=platform, persona_set=persona_set)
            elif persona_file == "HEART.md":
                self.record_persona_files(heart_path=file_path, platform=platform, persona_set=persona_set)
            elif persona_file == "IDENTITY.md":
                self.record_persona_files(identity_path=file_path, platform=platform, persona_set=persona_set)
            
            return True
        except Exception as e:
            print(f"Error recording persona update: {e}")
            return False
    
    def track_evolution(
        self,
        entity_id: str,
        new_content: str,
        new_properties: Optional[Dict] = None
    ) -> bool:
        """
        Track entity evolution by creating evolves_from relationship.
        
        Args:
            entity_id: Entity ID
            new_content: New content
            new_properties: New properties
        
        Returns:
            True if successful, False otherwise
        """
        # Get existing entity
        existing = self.database.get_entity(entity_id)
        if not existing:
            return False
        
        # Create new entity version
        new_entity_id = f"{entity_id}:v{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            # Insert new entity
            self.database.insert_entity(
                entity_id=new_entity_id,
                entity_type=existing['entity_type'],
                content=new_content,
                agent_id=existing.get('agent_id'),
                platform=existing.get('platform'),
                properties=new_properties or existing.get('properties', {})
            )
            
            # Create evolves_from relationship
            self.database.insert_relation(
                from_entity_id=new_entity_id,
                to_entity_id=entity_id,
                relation_type='evolves_from'
            )
            
            return True
        except Exception as e:
            print(f"Error tracking evolution: {e}")
            return False
