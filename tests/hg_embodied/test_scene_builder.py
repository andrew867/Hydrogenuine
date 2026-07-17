from __future__ import annotations

import pytest

from hg_embodied.isaac_bridge.scene_builder import build_scene, list_scenes


def test_list_scenes_includes_warehouse():
    assert "warehouse" in list_scenes()


def test_build_scene_table_block():
    scene = build_scene("table_block")
    assert scene["scene_id"] == "table_block"
    assert any(o.get("type") == "block" for o in scene["objects"])


def test_unknown_scene_raises():
    with pytest.raises(ValueError):
        build_scene("nonexistent")
