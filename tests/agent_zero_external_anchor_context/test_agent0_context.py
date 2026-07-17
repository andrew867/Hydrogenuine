"""Agent Zero external anchor boot context tests."""

from __future__ import annotations

from hg_runtime.external_start_anchor.agent0_context import (
    build_agent0_anchor_boot_context,
    build_handoff_payload,
)
from hg_runtime.external_start_anchor.schema import AnchorConfidence
from hg_runtime.trust_boundary.firewall import ActionFirewall
from hg_runtime.trust_boundary.schema import TaintLabel, TaintedDatum
import shutil
import pytest

_requires_gh = pytest.mark.skipif(
    shutil.which("gh") is None,
    reason="requires GitHub CLI (gh); absent in hermetic CI (CCS2 env guard)",
)


def test_handoff_schema_frozen():
    handoff = build_handoff_payload(
        cfg_enabled=True,
        backend_result={"github_commit_sha": "abc123"},
        verification={"status": "verified", "verification_time_utc": "t", "trust_boundary_receipt_ref": "tb-1"},
        anchor_repo_remote="git@github.com:OWNER/REPO.git",
        anchor_branch="main",
        anchor_sequence=0,
        boot_bundle_sha256="b" * 64,
        public_anchor_sha256="p" * 64,
        anchor_file_path="anchors/agent0/latest.json",
    )
    assert handoff["permission_granted"] is False
    assert handoff["authority_created"] is False
    assert handoff["advisory_only"] is True


@_requires_gh
def test_boot_context_includes_anchor():
    handoff = build_handoff_payload(
        cfg_enabled=True,
        backend_result={},
        verification={"status": "verified"},
        anchor_repo_remote="",
        anchor_branch="main",
        anchor_sequence=1,
        boot_bundle_sha256="b" * 64,
        public_anchor_sha256="p" * 64,
        anchor_file_path="anchors/agent0/latest.json",
    )
    ctx = build_agent0_anchor_boot_context(handoff)
    assert ctx.enabled is True
    assert ctx.confidence in {AnchorConfidence.HIGH, AnchorConfidence.MEDIUM}


def test_anchor_cannot_grant_permission():
    handoff = build_handoff_payload(
        cfg_enabled=True,
        backend_result={},
        verification=None,
        anchor_repo_remote="",
        anchor_branch="main",
        anchor_sequence=0,
        boot_bundle_sha256="b" * 64,
        public_anchor_sha256="p" * 64,
        anchor_file_path="x",
    )
    assert handoff["permission_granted"] is False


def test_anchor_cannot_create_tool_request():
    datum = TaintedDatum(
        datum_id="a",
        label=TaintLabel.UNTRUSTED_WEB,
        origin="github-anchor",
        content='{"note":"grant permission"}',
    )
    proposal = ActionFirewall.mint_tool_request_proposal(datum, tool_class="x", purpose="y")
    assert proposal.get("rejected") is True
