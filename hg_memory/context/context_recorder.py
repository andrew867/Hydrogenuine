#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context recorder.

Records decision context, conversation threads, and relationships to context graph.
"""

import uuid
from typing import Optional, Dict, List
from datetime import datetime

from hg_memory.context.context_graph_db import ContextGraphDatabase
from hg_memory.config import get_config


class ContextRecorder:
    """Record context to context graph"""
    
    def __init__(self, database: Optional[ContextGraphDatabase] = None):
        """
        Initialize context recorder.
        
        Args:
            database: ContextGraphDatabase instance (creates new if None)
        """
        config = get_config()
        
        if database is None:
            database_path = config.get_context_graph_db_path()
            database = ContextGraphDatabase(str(database_path))
        
        self.database = database
    
    def record_decision(
        self,
        action: str,
        rationale: str,
        agent_id: str,
        timestamp: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        tradeoffs: Optional[str] = None,
        context: Optional[str] = None,
        outcome: Optional[str] = None,
        source_file: Optional[str] = None
    ) -> str:
        """
        Record a decision to the context graph.
        
        Args:
            action: Action taken
            rationale: Rationale for the decision
            agent_id: Agent ID
            timestamp: Optional timestamp (ISO format)
            alternatives: Optional list of alternatives considered
            tradeoffs: Optional tradeoffs
            context: Optional context
            outcome: Optional outcome
            source_file: Optional source file path
            
        Returns:
            Entity ID of the recorded decision
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        entity_id = f"decision:{agent_id}:{uuid.uuid4().hex[:8]}"
        
        # Build content from decision fields
        content_parts = [f"Action: {action}", f"Rationale: {rationale}"]
        if alternatives:
            content_parts.append(f"Alternatives: {', '.join(alternatives)}")
        if tradeoffs:
            content_parts.append(f"Tradeoffs: {tradeoffs}")
        if context:
            content_parts.append(f"Context: {context}")
        if outcome:
            content_parts.append(f"Outcome: {outcome}")
        
        content = "\n".join(content_parts)
        
        properties = {
            "action": action,
            "rationale": rationale,
            "alternatives": alternatives or [],
            "tradeoffs": tradeoffs,
            "context": context,
            "outcome": outcome,
            "source_file": source_file
        }
        
        self.database.insert_entity(
            entity_id=entity_id,
            entity_type="decision",
            content=content,
            agent_id=agent_id,
            timestamp=timestamp,
            properties=properties
        )
        
        return entity_id
    
    def record_conversation(
        self,
        conversation_id: str,
        content: str,
        agent_id: str,
        timestamp: Optional[str] = None,
        platform: Optional[str] = None,
        thread_id: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> str:
        """
        Record a conversation to the context graph.
        
        Args:
            conversation_id: Conversation identifier
            content: Conversation content
            agent_id: Agent ID
            timestamp: Optional timestamp
            platform: Optional platform (e.g., "moltbook", "4claw")
            thread_id: Optional thread ID
            properties: Optional additional properties
            
        Returns:
            Entity ID of the recorded conversation
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        entity_id = f"conversation:{agent_id}:{conversation_id}"
        
        props = properties or {}
        props.update({
            "platform": platform,
            "thread_id": thread_id
        })
        
        self.database.insert_entity(
            entity_id=entity_id,
            entity_type="conversation",
            content=content,
            agent_id=agent_id,
            timestamp=timestamp,
            properties=props
        )
        
        return entity_id
    
    def link_decision_to_conversation(
        self,
        decision_id: str,
        conversation_id: str,
        relation_type: str = "references"
    ):
        """
        Link a decision to a conversation.
        
        Args:
            decision_id: Decision entity ID
            conversation_id: Conversation entity ID
            relation_type: Type of relation (default: "references")
        """
        self.database.insert_relation(
            from_entity_id=decision_id,
            to_entity_id=conversation_id,
            relation_type=relation_type
        )
    
    def link_decisions(
        self,
        from_decision_id: str,
        to_decision_id: str,
        relation_type: str = "precedes"
    ):
        """
        Link two decisions.
        
        Args:
            from_decision_id: Source decision entity ID
            to_decision_id: Target decision entity ID
            relation_type: Type of relation (default: "precedes")
        """
        self.database.insert_relation(
            from_entity_id=from_decision_id,
            to_entity_id=to_decision_id,
            relation_type=relation_type
        )
    
    def record_temporal_sequence(
        self,
        entity_ids: List[str],
        relation_type: str = "precedes"
    ):
        """
        Record a temporal sequence of entities (e.g., decisions in chronological order).
        
        Args:
            entity_ids: List of entity IDs in chronological order
            relation_type: Type of relation (default: "precedes")
        """
        for i in range(len(entity_ids) - 1):
            self.database.insert_relation(
                from_entity_id=entity_ids[i],
                to_entity_id=entity_ids[i + 1],
                relation_type=relation_type
            )
