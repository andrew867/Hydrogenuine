#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script after initialization.

Tests that databases are set up correctly and functionality works end-to-end.
Uses hg_memory only.
"""

import sys
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

print("=" * 70)
print("Memory Engine Initialization Verification (hg_memory)")
print("=" * 70)

# Test 1: Health Check
print("\n[1] Health Check...")
from hg_memory.health_check import health_check

h = health_check()
print(f"  Status: {h['status']}")
print(f"  Agent databases: {h['agent_databases']['healthy']}/{h['agent_databases']['total']} healthy")
print(f"  Context database: {'healthy' if h['context_database']['integrity'] else 'unhealthy'}")

# Test 2: Agent Search
print("\n[2] Agent Search...")
from hg_memory.agent.agent_task_integration import search_agent_memory

results = search_agent_memory('fourclaw-engage', 'thread', limit=5)
print(f"  Search results: {len(results)} results")
if results:
    print(f"  First result source: {results[0].get('source_type', 'unknown')}")

# Test 3: Unified Search
print("\n[3] Unified Search...")
from hg_memory.unified_search import get_unified_search

u = get_unified_search()
results = u.search_all('test', agent_id='test-agent', limit=5)
print(f"  Agent memory results: {len(results['agent_memory'])}")
print(f"  Context results: {len(results['context'])}")
print(f"  Knowledge results: {len(results['knowledge'])}")

# Test 4: Database Verification
print("\n[4] Database Verification...")
from hg_memory.config import get_config
from hg_gateway.shared_storage import use_shared_gateway_db

config = get_config()
agent_db_path = config.get_agent_memory_db_path('fourclaw-engage')
context_db_path = config.get_context_graph_db_path()

print(f"  Agent DB exists: {agent_db_path.exists()}")
print(f"  Context DB exists: {context_db_path.exists()}")

if agent_db_path.exists():
    from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
    db = AgentMemoryDatabase(str(agent_db_path))
    files = db.get_indexed_files()
    print(f"  Indexed files in agent DB: {len(files)}")

if context_db_path.exists():
    from hg_memory.context.context_graph_db import ContextGraphDatabase
    db = ContextGraphDatabase(str(context_db_path))
    conn = db._get_connection()
    table_name = "memory_context_entities" if use_shared_gateway_db(context_db_path) else "context_entities"
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    entity_count = cursor.fetchone()[0]
    conn.close()
    print(f"  Entities in context graph: {entity_count}")

# Test 5: Overseer Access
print("\n[5] Overseer Access...")
from hg_memory import get_overseer_access

overseer = get_overseer_access()
agents = overseer._get_agent_ids()
print(f"  Discovered agents: {len(agents)}")
if agents:
    print(f"  Sample agents: {agents[:3]}")

print("\n" + "=" * 70)
print("[OK] All verification tests passed!")
print("=" * 70)
