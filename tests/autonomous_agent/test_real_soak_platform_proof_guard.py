"""Platform proof guard tests."""
from hg_runtime.real_soak_launch.platform_proof_guard import evaluate_platform_proof, proof_missing_cannot_be_green
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict


def test_missing_proof_red():
    d = evaluate_platform_proof(content_sha256="abc", platform_object_id=None, platform_url=None, proof_content_sha256=None, dispatch_receipt_ref=None)
    assert d.verdict == RealSoakLaunchVerdict.RED_NO_PROOF.value
    assert proof_missing_cannot_be_green(d.verdict)


def test_delayed_yellow():
    d = evaluate_platform_proof(content_sha256="abc", platform_object_id="1", platform_url="http://x", proof_content_sha256="abc", dispatch_receipt_ref="d1", proof_delayed=True)
    assert d.verdict == RealSoakLaunchVerdict.YELLOW_PROOF_DELAYED.value


def test_content_mismatch_red():
    d = evaluate_platform_proof(content_sha256="abc", platform_object_id="1", platform_url="http://x", proof_content_sha256="def", dispatch_receipt_ref="d1")
    assert d.verdict == RealSoakLaunchVerdict.RED_CONTENT_MISMATCH.value


def test_ok_with_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.external_write_authority.action_ledger.LEDGER_DIR", tmp_path)
    d = evaluate_platform_proof(content_sha256="abc", platform_object_id="post-1", platform_url="http://x", proof_content_sha256="abc", dispatch_receipt_ref="dispatch-1")
    assert d.verdict == "GREEN_PLATFORM_PROOF_OK"
    assert d.ledger_entry_ref
