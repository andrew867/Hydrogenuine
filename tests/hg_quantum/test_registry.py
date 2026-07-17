from __future__ import annotations

from hg_quantum.registry import build_default_registry


def test_registry_lists_all_wave2_models():
    reg = build_default_registry(fingerprint_id="fp_reg")
    models = reg.list_models()
    ids = {m["model_id"] for m in models}
    assert "varifocal_router" in ids
    assert "temporal_auth" in ids
    assert "kpz_predictor" in ids
    assert len(models) == 7


def test_registry_diagnostics():
    reg = build_default_registry()
    reg.get_instance("varifocal_router")
    diag = reg.diagnostics("varifocal_router")
    assert diag["ok"] is True
