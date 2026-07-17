"""Tool capability fabric tests."""

from hg_runtime.tool_capability_fabric.registry import load_registry


def test_registry_loads():
    reg = load_registry()
    assert len(reg.capabilities) >= 20


def test_no_capability_grants_permission():
    reg = load_registry()
    for cap in reg.capabilities.values():
        assert cap.permission_granted is False
        assert cap.authority_created is False


def test_manifest_builds():
    reg = load_registry()
    m = reg.build_manifest(organ_id="organ:Agent0")
    assert m["permission_granted"] is False
    assert m["capability_count"] > 0
