#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analytics and reporting for identity graph system.

Provides statistics, evolution reports, and identity analytics.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter

from .identity_graph_db import IdentityGraphDatabase
from .identity_search import IdentitySearch
from .config import get_identity_graph_db_path


class IdentityAnalytics:
    """Analytics and reporting for identity graph"""
    
    def __init__(self, database: IdentityGraphDatabase):
        """
        Initialize analytics interface.
        
        Args:
            database: IdentityGraphDatabase instance
        """
        self.database = database
        self.search = IdentitySearch(database)

    def _entity_table(self) -> str:
        return "memory_identity_entities" if self.database._shared_gateway_db else "identity_entities"

    def _relation_table(self) -> str:
        return "memory_identity_relations" if self.database._shared_gateway_db else "identity_relations"

    def _version_table(self) -> str:
        return "memory_identity_versions" if self.database._shared_gateway_db else "identity_versions"

    def _pattern_table(self) -> str:
        return "memory_identity_patterns" if self.database._shared_gateway_db else "identity_patterns"
    
    def get_identity_statistics(
        self,
        agent_id: Optional[str] = None,
        platform: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get comprehensive identity statistics.
        
        Args:
            agent_id: Optional agent ID filter
            platform: Optional platform filter
            
        Returns:
            Dictionary with identity statistics
        """
        conn = self.database._get_connection()
        try:
            entity_table = self._entity_table()
            relation_table = self._relation_table()
            version_table = self._version_table()
            pattern_table = self._pattern_table()
            stats = {
                'total_entities': 0,
                'total_relations': 0,
                'total_versions': 0,
                'total_patterns': 0,
                'entity_types': {},
                'relation_types': {},
                'layers': {
                    'identity': 0,
                    'soul': 0,
                    'heart': 0,
                    'expression': 0
                },
                'platforms': {},
                'timeline': {
                    'first_recorded': None,
                    'last_updated': None,
                    'total_updates': 0
                }
            }
            
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if agent_id:
                where_clauses.append("agent_id = ?")
                params.append(agent_id)
            
            if platform:
                where_clauses.append("platform = ?")
                params.append(platform)
            
            where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
            base_where = "WHERE deleted_at IS NULL" + (" AND " + " AND ".join(where_clauses) if where_clauses else "")
            
            # Entity count
            cursor = conn.execute(f"SELECT COUNT(*) FROM {entity_table} {base_where}", params)
            stats['total_entities'] = cursor.fetchone()[0]
            
            # Relation count
            if where_clauses:
                rel_where = "WHERE " + " AND ".join([f"from_entity_id IN (SELECT entity_id FROM {entity_table} {base_where})"] + 
                                                   [f"to_entity_id IN (SELECT entity_id FROM {entity_table} {base_where})"])
                cursor = conn.execute(f"SELECT COUNT(*) FROM {relation_table} {rel_where}", params + params)
            else:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {relation_table}")
            stats['total_relations'] = cursor.fetchone()[0]
            
            # Version count
            if where_clauses:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {version_table} WHERE {' AND '.join(where_clauses)}", params)
            else:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {version_table}")
            stats['total_versions'] = cursor.fetchone()[0]
            
            # Pattern count
            if where_clauses:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {pattern_table} WHERE {' AND '.join(where_clauses)}", params)
            else:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {pattern_table}")
            stats['total_patterns'] = cursor.fetchone()[0]
            
            # Entity types distribution
            cursor = conn.execute(f"SELECT entity_type, COUNT(*) FROM {entity_table} {base_where} GROUP BY entity_type", params)
            for row in cursor.fetchall():
                stats['entity_types'][row[0]] = row[1]
                
                # Map to layer
                entity_type = row[0]
                if entity_type in ["name", "role", "audience", "scope", "non_negotiable", "negotiable",
                                  "competency", "deferral", "voice", "formatting", "tool_permission", "escalation_rule"]:
                    stats['layers']['identity'] += row[1]
                elif entity_type in ["mission", "good_evil", "ideal", "goal", "priority_order", "tradeoff_policy",
                                    "truthfulness_policy", "alignment", "belief", "value"]:
                    stats['layers']['soul'] += row[1]
                elif entity_type in ["empathy_level", "emotional_stance", "anger_handling", "insult_handling",
                                    "crisis_handling", "correction_style", "question_style", "de_escalation",
                                    "escalation", "priority"]:
                    stats['layers']['heart'] += row[1]
                elif entity_type in ["trait", "speech_pattern", "emotion", "catchphrase", "engagement_pattern"]:
                    stats['layers']['expression'] += row[1]
            
            # Relation types distribution
            if where_clauses:
                rel_where = "WHERE from_entity_id IN (SELECT entity_id FROM {entity_table} {base_where})".format(entity_table=entity_table, base_where=base_where)
                cursor = conn.execute(f"SELECT relation_type, COUNT(*) FROM {relation_table} {rel_where} GROUP BY relation_type", params)
            else:
                cursor = conn.execute(f"SELECT relation_type, COUNT(*) FROM {relation_table} GROUP BY relation_type")
            for row in cursor.fetchall():
                stats['relation_types'][row[0]] = row[1]
            
            # Platform distribution
            cursor = conn.execute(f"SELECT platform, COUNT(*) FROM {entity_table} {base_where} AND platform IS NOT NULL GROUP BY platform", params)
            for row in cursor.fetchall():
                stats['platforms'][row[0]] = row[1]
            
            # Timeline
            cursor = conn.execute(f"SELECT MIN(created_at), MAX(updated_at), COUNT(*) FROM {entity_table} {base_where}", params)
            timeline_row = cursor.fetchone()
            if timeline_row and timeline_row[0]:
                stats['timeline']['first_recorded'] = timeline_row[0]
                stats['timeline']['last_updated'] = timeline_row[1] or timeline_row[0]
                stats['timeline']['total_updates'] = timeline_row[2]
            
            return stats
        finally:
            conn.close()
    
    def get_evolution_report(
        self,
        agent_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, any]:
        """
        Get evolution report showing identity changes over time.
        
        Args:
            agent_id: Optional agent ID filter
            days: Number of days to look back
            
        Returns:
            Dictionary with evolution statistics
        """
        conn = self.database._get_connection()
        try:
            entity_table = self._entity_table()
            relation_table = self._relation_table()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            report = {
                'period_days': days,
                'total_evolutions': 0,
                'evolutions_by_type': {},
                'most_evolved_entities': [],
                'evolution_timeline': []
            }
            
            # Count evolves_from relations
            if agent_id:
                cursor = conn.execute(f"""
                    SELECT 
                        e.entity_type,
                        COUNT(*) as count
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE r.relation_type = 'evolves_from'
                      AND e.agent_id = ?
                      AND r.timestamp >= ?
                    GROUP BY e.entity_type
                """, (agent_id, cutoff_date))
            else:
                cursor = conn.execute(f"""
                    SELECT 
                        e.entity_type,
                        COUNT(*) as count
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE r.relation_type = 'evolves_from'
                      AND r.timestamp >= ?
                    GROUP BY e.entity_type
                """, (cutoff_date,))
            
            for row in cursor.fetchall():
                report['evolutions_by_type'][row[0]] = row[1]
                report['total_evolutions'] += row[1]
            
            # Get most evolved entities
            if agent_id:
                cursor = conn.execute(f"""
                    SELECT 
                        r.from_entity_id,
                        e.entity_type,
                        COUNT(*) as evolution_count
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE r.relation_type = 'evolves_from'
                      AND e.agent_id = ?
                      AND r.timestamp >= ?
                    GROUP BY r.from_entity_id, e.entity_type
                    ORDER BY evolution_count DESC
                    LIMIT 10
                """, (agent_id, cutoff_date))
            else:
                cursor = conn.execute(f"""
                    SELECT 
                        r.from_entity_id,
                        e.entity_type,
                        COUNT(*) as evolution_count
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE r.relation_type = 'evolves_from'
                      AND r.timestamp >= ?
                    GROUP BY r.from_entity_id, e.entity_type
                    ORDER BY evolution_count DESC
                    LIMIT 10
                """, (cutoff_date,))
            
            for row in cursor.fetchall():
                entity = self.database.get_entity(row[0])
                if entity:
                    report['most_evolved_entities'].append({
                        'entity_id': row[0],
                        'entity_type': row[1],
                        'evolution_count': row[2],
                        'content': entity.get('content', '')[:100]  # First 100 chars
                    })
            
            # Get evolution timeline
            if agent_id:
                cursor = conn.execute(f"""
                    SELECT 
                        DATE(r.timestamp) as date,
                        COUNT(*) as count
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE r.relation_type = 'evolves_from'
                      AND e.agent_id = ?
                      AND r.timestamp >= ?
                    GROUP BY DATE(r.timestamp)
                    ORDER BY date
                """, (agent_id, cutoff_date))
            else:
                cursor = conn.execute(f"""
                    SELECT 
                        DATE(r.timestamp) as date,
                        COUNT(*) as count
                    FROM {relation_table} r
                    WHERE r.relation_type = 'evolves_from'
                      AND r.timestamp >= ?
                    GROUP BY DATE(r.timestamp)
                    ORDER BY date
                """, (cutoff_date,))
            
            for row in cursor.fetchall():
                report['evolution_timeline'].append({
                    'date': row[0],
                    'count': row[1]
                })
            
            return report
        finally:
            conn.close()
    
    def get_conflict_report(
        self,
        agent_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get conflict report showing conflicting identity elements.
        
        Args:
            agent_id: Optional agent ID filter
            
        Returns:
            Dictionary with conflict statistics
        """
        conflicts = self.search.find_conflicts(agent_id=agent_id)
        
        report = {
            'total_conflicts': len(conflicts),
            'conflicts_by_type': {},
            'conflicting_pairs': []
        }
        
        # Analyze conflicts
        for conflict in conflicts:
            from_type = conflict.get('from_type', 'unknown')
            to_type = conflict.get('to_type', 'unknown')
            pair_key = f"{from_type} <-> {to_type}"
            
            report['conflicts_by_type'][pair_key] = report['conflicts_by_type'].get(pair_key, 0) + 1
            
            report['conflicting_pairs'].append({
                'from_entity': conflict.get('from_entity', {}),
                'to_entity': conflict.get('to_entity', {}),
                'from_type': from_type,
                'to_type': to_type,
                'timestamp': conflict.get('timestamp')
            })
        
        return report
    
    def get_layer_analysis(
        self,
        agent_id: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Get detailed analysis by identity layer.
        
        Args:
            agent_id: Optional agent ID filter
            
        Returns:
            Dictionary mapping layer names to analysis data
        """
        analysis = {
            'identity': {'entities': [], 'count': 0, 'types': {}},
            'soul': {'entities': [], 'count': 0, 'types': {}},
            'heart': {'entities': [], 'count': 0, 'types': {}},
            'expression': {'entities': [], 'count': 0, 'types': {}}
        }
        
        for layer in ['identity', 'soul', 'heart', 'expression']:
            entities = self.search.search_by_layer(layer, agent_id=agent_id, limit=1000)
            analysis[layer]['count'] = len(entities)
            analysis[layer]['entities'] = entities[:10]  # Top 10
            
            # Count by type
            for entity in entities:
                entity_type = entity.get('entity_type', 'unknown')
                analysis[layer]['types'][entity_type] = analysis[layer]['types'].get(entity_type, 0) + 1
        
        return analysis
    
    def get_version_history_report(
        self,
        agent_id: Optional[str] = None,
        persona_file: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get version history report for persona files.
        
        Args:
            agent_id: Optional agent ID filter
            persona_file: Optional persona file filter (SOUL.md, HEART.md, IDENTITY.md)
            
        Returns:
            Dictionary with version history statistics
        """
        files = ['SOUL.md', 'HEART.md', 'IDENTITY.md']
        if persona_file:
            files = [persona_file]
        
        report = {
            'total_versions': 0,
            'files': {}
        }
        
        for file_name in files:
            history = self.search.get_version_history(file_name, agent_id=agent_id, limit=1000)
            report['files'][file_name] = {
                'version_count': len(history),
                'first_version': history[-1] if history else None,
                'latest_version': history[0] if history else None,
                'versions': history[:10]  # Most recent 10
            }
            report['total_versions'] += len(history)
        
        return report
    
    def get_relationship_network(
        self,
        agent_id: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get relationship network analysis.
        
        Args:
            agent_id: Optional agent ID filter
            entity_type: Optional entity type filter
            
        Returns:
            Dictionary with network statistics
        """
        conn = self.database._get_connection()
        try:
            entity_table = self._entity_table()
            relation_table = self._relation_table()
            network = {
                'total_nodes': 0,
                'total_edges': 0,
                'relation_distribution': {},
                'most_connected_entities': [],
                'isolated_entities': 0
            }
            
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if agent_id:
                where_clauses.append("e.agent_id = ?")
                params.append(agent_id)
            
            if entity_type:
                where_clauses.append("e.entity_type = ?")
                params.append(entity_type)
            
            where_sql = "WHERE e.deleted_at IS NULL" + (" AND " + " AND ".join(where_clauses) if where_clauses else "")
            
            # Count nodes
            cursor = conn.execute(f"SELECT COUNT(*) FROM {entity_table} e {where_sql}", params)
            network['total_nodes'] = cursor.fetchone()[0]
            
            # Count edges
            if where_clauses:
                # Build subquery for entity IDs (without alias in subquery)
                subquery_clauses = []
                subquery_params = []
                if agent_id:
                    subquery_clauses.append("agent_id = ?")
                    subquery_params.append(agent_id)
                if entity_type:
                    subquery_clauses.append("entity_type = ?")
                    subquery_params.append(entity_type)
                subquery_where = "WHERE deleted_at IS NULL" + (" AND " + " AND ".join(subquery_clauses) if subquery_clauses else "")
                edge_where = f"WHERE from_entity_id IN (SELECT entity_id FROM {entity_table} {subquery_where})"
                cursor = conn.execute(f"SELECT COUNT(*) FROM {relation_table} {edge_where}", subquery_params)
            else:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {relation_table}")
            network['total_edges'] = cursor.fetchone()[0]
            
            # Relation type distribution
            if where_clauses:
                cursor = conn.execute(f"""
                    SELECT relation_type, COUNT(*) 
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE e.deleted_at IS NULL AND {' AND '.join(where_clauses)}
                    GROUP BY relation_type
                """, params)
            else:
                cursor = conn.execute(f"SELECT relation_type, COUNT(*) FROM {relation_table} GROUP BY relation_type")
            
            for row in cursor.fetchall():
                network['relation_distribution'][row[0]] = row[1]
            
            # Most connected entities
            if where_clauses:
                cursor = conn.execute(f"""
                    SELECT 
                        r.from_entity_id,
                        COUNT(*) as connection_count
                    FROM {relation_table} r
                    JOIN {entity_table} e ON r.from_entity_id = e.entity_id
                    WHERE e.deleted_at IS NULL AND {' AND '.join(where_clauses)}
                    GROUP BY r.from_entity_id
                    ORDER BY connection_count DESC
                    LIMIT 10
                """, params)
            else:
                cursor = conn.execute(f"""
                    SELECT 
                        from_entity_id,
                        COUNT(*) as connection_count
                    FROM {relation_table}
                    GROUP BY from_entity_id
                    ORDER BY connection_count DESC
                    LIMIT 10
                """)
            
            for row in cursor.fetchall():
                entity = self.database.get_entity(row[0])
                if entity:
                    network['most_connected_entities'].append({
                        'entity_id': row[0],
                        'entity_type': entity.get('entity_type', 'unknown'),
                        'connection_count': row[1],
                        'content': entity.get('content', '')[:100]
                    })
            
            # Count isolated entities (no relations)
            if where_clauses:
                cursor = conn.execute(f"""
                    SELECT COUNT(*)
                    FROM {entity_table} e
                    WHERE e.deleted_at IS NULL
                      AND {' AND '.join(where_clauses)}
                      AND e.entity_id NOT IN (
                          SELECT DISTINCT from_entity_id FROM {relation_table}
                          UNION
                          SELECT DISTINCT to_entity_id FROM {relation_table}
                      )
                """, params)
            else:
                cursor = conn.execute(f"""
                    SELECT COUNT(*)
                    FROM {entity_table}
                    WHERE deleted_at IS NULL
                      AND entity_id NOT IN (
                          SELECT DISTINCT from_entity_id FROM {relation_table}
                          UNION
                          SELECT DISTINCT to_entity_id FROM {relation_table}
                      )
                """)
            
            network['isolated_entities'] = cursor.fetchone()[0]
            
            return network
        finally:
            conn.close()
