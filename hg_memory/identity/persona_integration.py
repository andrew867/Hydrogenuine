#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persona system integration.

Integrates identity graph system with persona_loader.py for automatic
extraction and recording when persona files are updated.
"""

from pathlib import Path
from typing import Optional
import threading

# Try to import identity recorder (optional - graceful degradation)
try:
    from .identity_recorder import IdentityRecorder
    IDENTITY_SYSTEM_AVAILABLE = True
except ImportError:
    IDENTITY_SYSTEM_AVAILABLE = False


# Feature flag - can be disabled if needed
IDENTITY_TRACKING_ENABLED = True


def get_agent_id_from_platform(platform: str) -> Optional[str]:
    """
    Get agent ID from platform identifier.
    
    Args:
        platform: Platform identifier (e.g., "fourclaw", "aichan")
    
    Returns:
        Agent ID or None if not determinable
    """
    # Map platforms to agent IDs
    platform_to_agent = {
        "fourclaw": "fourclaw-auto-post",
        "aichan": "aichan-auto-post",
        "moltbook": "moltbook-auto-post",
        "moltx": "moltx-auto-post"
    }
    
    return platform_to_agent.get(platform)


def record_persona_update_async(
    platform: str,
    persona_set: str,
    file_name: str,
    file_path: Path,
    before_content: Optional[str] = None,
    after_content: Optional[str] = None
) -> None:
    """
    Record persona file update to identity graph asynchronously.
    
    This function is called after persona file is updated. It runs in a
    separate thread to avoid blocking the persona update operation.
    
    Args:
        platform: Platform identifier
        persona_set: Persona set identifier
        file_name: Persona file name (SOUL.md, HEART.md, IDENTITY.md)
        file_path: Path to persona file
        before_content: Content before update (optional)
        after_content: Content after update (optional)
    """
    if not IDENTITY_SYSTEM_AVAILABLE or not IDENTITY_TRACKING_ENABLED:
        return
    
    def _record_update():
        """Internal function to record update in background thread"""
        try:
            agent_id = get_agent_id_from_platform(platform)
            if not agent_id:
                # Can't determine agent ID, skip
                return
            
            recorder = IdentityRecorder(agent_id=agent_id)
            
            # Record the update
            recorder.record_persona_update(
                persona_file=file_name,
                file_path=file_path,
                before_content=before_content,
                after_content=after_content,
                platform=platform,
                persona_set=persona_set
            )
        except Exception as e:
            # Log error but don't crash
            print(f"Warning: Failed to record persona update to identity graph: {e}")
    
    # Run in background thread
    thread = threading.Thread(target=_record_update, daemon=True)
    thread.start()


def record_persona_files_async(
    platform: str,
    persona_set: str,
    agent_id: Optional[str] = None
) -> None:
    """
    Record all persona files for a platform/persona_set asynchronously.
    
    This can be called to index existing persona files.
    
    Args:
        platform: Platform identifier
        persona_set: Persona set identifier
        agent_id: Optional agent ID (will be derived from platform if not provided)
    """
    if not IDENTITY_SYSTEM_AVAILABLE or not IDENTITY_TRACKING_ENABLED:
        return
    
    def _record_files():
        """Internal function to record files in background thread"""
        try:
            # Determine agent_id
            final_agent_id = agent_id
            if final_agent_id is None:
                final_agent_id = get_agent_id_from_platform(platform)
                if not final_agent_id:
                    return
            
            recorder = IdentityRecorder(agent_id=final_agent_id)
            
            # Get persona file paths
            persona_dir = Path(f"skills/automation/personas/{platform}/{persona_set}")
            soul_path = persona_dir / "SOUL.md"
            heart_path = persona_dir / "HEART.md"
            identity_path = persona_dir / "IDENTITY.md"
            
            # Record all files
            recorder.record_persona_files(
                soul_path=soul_path if soul_path.exists() else None,
                heart_path=heart_path if heart_path.exists() else None,
                identity_path=identity_path if identity_path.exists() else None,
                platform=platform,
                persona_set=persona_set
            )
        except Exception as e:
            print(f"Warning: Failed to record persona files to identity graph: {e}")
    
    # Run in background thread
    thread = threading.Thread(target=_record_files, daemon=True)
    thread.start()
