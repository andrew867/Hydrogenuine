#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI tools for identity graph system.

Provides command-line interface for identity graph operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .identity_graph_db import IdentityGraphDatabase
from .identity_search import IdentitySearch
from .identity_analytics import IdentityAnalytics
from .identity_recorder import IdentityRecorder
from .identity_extractor import IdentityExtractor
from .identity_health import health_check
from .config import get_identity_graph_db_path


def cmd_search(args):
    """Search identity graph"""
    db_path = get_identity_graph_db_path(args.agent_id)
    if not db_path.exists():
        print(f"Error: Identity database not found for agent {args.agent_id}")
        return 1
    
    db = IdentityGraphDatabase(str(db_path))
    search = IdentitySearch(db)
    
    results = search.search_identity(
        query=args.query,
        agent_id=args.agent_id,
        entity_type=args.entity_type,
        limit=args.limit
    )
    
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"  - {result['entity_type']}: {result.get('content', '')[:80]}...")
    
    return 0


def cmd_stats(args):
    """Get identity statistics"""
    db_path = get_identity_graph_db_path(args.agent_id)
    if not db_path.exists():
        print(f"Error: Identity database not found for agent {args.agent_id}")
        return 1
    
    db = IdentityGraphDatabase(str(db_path))
    analytics = IdentityAnalytics(db)
    
    stats = analytics.get_identity_statistics(
        agent_id=args.agent_id,
        platform=args.platform
    )
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"Identity Statistics for {args.agent_id}:")
        print(f"  Total Entities: {stats['total_entities']}")
        print(f"  Total Relations: {stats['total_relations']}")
        print(f"  Total Versions: {stats['total_versions']}")
        print(f"  Total Patterns: {stats['total_patterns']}")
        print(f"\nLayers:")
        for layer, count in stats['layers'].items():
            print(f"  {layer}: {count}")
        print(f"\nEntity Types: {len(stats['entity_types'])} types")
        print(f"Relation Types: {len(stats['relation_types'])} types")
    
    return 0


def cmd_health(args):
    """Check identity graph health"""
    health = health_check(args.agent_id)
    
    if args.json:
        print(json.dumps(health, indent=2))
    else:
        print(f"Health Status: {health['status']}")
        print(f"Database Exists: {health['database_exists']}")
        print(f"Database Accessible: {health['database_accessible']}")
        print(f"Schema Version: {health['schema_version']}")
        print(f"Entity Count: {health['entity_count']}")
        print(f"Relation Count: {health['relation_count']}")
        if health['errors']:
            print(f"Errors: {', '.join(health['errors'])}")
    
    return 0 if health['status'] == 'healthy' else 1


def cmd_evolution(args):
    """Get evolution report"""
    db_path = get_identity_graph_db_path(args.agent_id)
    if not db_path.exists():
        print(f"Error: Identity database not found for agent {args.agent_id}")
        return 1
    
    db = IdentityGraphDatabase(str(db_path))
    analytics = IdentityAnalytics(db)
    
    report = analytics.get_evolution_report(
        agent_id=args.agent_id,
        days=args.days
    )
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Evolution Report (last {args.days} days):")
        print(f"  Total Evolutions: {report['total_evolutions']}")
        print(f"  Evolutions by Type:")
        for entity_type, count in report['evolutions_by_type'].items():
            print(f"    {entity_type}: {count}")
        print(f"\nMost Evolved Entities:")
        for entity in report['most_evolved_entities'][:5]:
            print(f"  - {entity['entity_type']}: {entity['evolution_count']} evolutions")
    
    return 0


def cmd_extract(args):
    """Extract identity from persona files"""
    extractor = IdentityExtractor()
    
    soul_path = Path(args.soul) if args.soul else None
    heart_path = Path(args.heart) if args.heart else None
    identity_path = Path(args.identity) if args.identity else None
    
    entities, patterns, relationships = extractor.extract_from_files(
        soul_path=soul_path,
        heart_path=heart_path,
        identity_path=identity_path
    )
    
    print(f"Extracted {len(entities)} entities, {len(patterns)} patterns, {len(relationships)} relationships")
    
    if args.json:
        output = {
            'entities': entities,
            'patterns': patterns,
            'relationships': relationships
        }
        print(json.dumps(output, indent=2))
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Identity Graph System CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search identity graph')
    search_parser.add_argument('agent_id', help='Agent ID')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--entity-type', help='Entity type filter')
    search_parser.add_argument('--limit', type=int, default=10, help='Result limit')
    search_parser.set_defaults(func=cmd_search)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Get identity statistics')
    stats_parser.add_argument('agent_id', help='Agent ID')
    stats_parser.add_argument('--platform', help='Platform filter')
    stats_parser.add_argument('--json', action='store_true', help='JSON output')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Check health')
    health_parser.add_argument('--agent-id', help='Agent ID (optional)')
    health_parser.add_argument('--json', action='store_true', help='JSON output')
    health_parser.set_defaults(func=cmd_health)
    
    # Evolution command
    evolution_parser = subparsers.add_parser('evolution', help='Get evolution report')
    evolution_parser.add_argument('agent_id', help='Agent ID')
    evolution_parser.add_argument('--days', type=int, default=30, help='Days to look back')
    evolution_parser.add_argument('--json', action='store_true', help='JSON output')
    evolution_parser.set_defaults(func=cmd_evolution)
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract from persona files')
    extract_parser.add_argument('--soul', help='Path to SOUL.md')
    extract_parser.add_argument('--heart', help='Path to HEART.md')
    extract_parser.add_argument('--identity', help='Path to IDENTITY.md')
    extract_parser.add_argument('--json', action='store_true', help='JSON output')
    extract_parser.set_defaults(func=cmd_extract)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
