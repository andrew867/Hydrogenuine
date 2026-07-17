"""GitHub anchor repo init tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hg_runtime.github_anchor_repo_init.deploy_key import generate_deploy_key
from hg_runtime.github_anchor_repo_init.hygiene import assert_no_private_key_material, verify_key_hygiene
from hg_runtime.github_anchor_repo_init.repo_init import init_witness_repo
from hg_runtime.github_anchor_repo_init.signing_key import generate_signing_key
from hg_runtime.github_anchor_repo_init.ssh_doctor import run_ssh_doctor

WORKSPACE = Path(__file__).resolve().parents[2]


def test_deploy_key_no_private_in_output():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_deploy_key(out_dir=Path(tmp))
        blob = json.dumps(result.to_payload())
        assert_no_private_key_material(blob)
        assert "BEGIN OPENSSH PRIVATE KEY" not in blob
        assert result.public_key_contents.startswith("ssh-ed25519")


def test_signing_key_openssl_or_crypto():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_signing_key(out_dir=Path(tmp))
        blob = json.dumps(result.to_payload())
        assert_no_private_key_material(blob)
        assert result.signer_key_id
        assert Path(tmp, "agent_zero_anchor_ed25519.pem").exists()


def test_witness_repo_layout():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "witness"
        result = init_witness_repo(repo_path=repo, remote="", push=False)
        assert result.verdict.startswith("GREEN")
        assert (repo / "anchors/agent0/latest.json").exists()
        assert (repo / "anchors/agent0_journal/chain.json").exists()
        assert "no secrets" in (repo / "README.md").read_text().lower()


def test_ssh_doctor_offline_yellow():
    result = run_ssh_doctor(live_test=False)
    assert result.verdict.startswith(("YELLOW", "GREEN"))
    blob = json.dumps(result.to_payload())
    assert "BEGIN OPENSSH PRIVATE KEY" not in blob


def test_private_key_not_tracked_in_temp():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_deploy_key(out_dir=Path(tmp))
        hygiene = verify_key_hygiene(result.private_key_path, workspace=WORKSPACE)
        assert hygiene["private_key_tracked"] is False
