"""SLE-RC end-to-end soak runner."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.dtx_manifest import build_dtx_manifest
from hg_runtime.document_text_exchange.dtx_pipeline import run_dtx_pipeline
from hg_runtime.document_text_exchange.dtx_soak_runner import run_dtx_document_soak
from hg_runtime.document_text_exchange.schemas import DTX_APPROVED_ROOT
from hg_runtime.operator_evidence_corpus.fixtures import build_oec0_fixture_records
from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result
from hg_runtime.safe_local_evidence_rc.rc_mutation_summary import build_rc_mutation_summary
from hg_runtime.safe_local_evidence_rc.rc_replay import build_rc_soak_iteration, build_rc_soak_manifest, rc_stable_hash
from hg_runtime.safe_local_evidence_rc.schemas import RC_SOAK_ITERATION_COUNT, assert_neutral, neutral_flags, record_hash


def _explicit_manifest_refs(root: Path) -> dict:
    oec = build_oec0_fixture_records()
    dtx_manifest = build_dtx_manifest(
        manifest_id="sle-rc-dtx-manifest-ref",
        fixture_paths=[f"{DTX_APPROVED_ROOT}/family_01/plain_support.txt"],
        fixture_ids=["dtx-fixture-ref"],
        family_ids=["PLAIN_TEXT_SUPPORT"],
    )
    return {
        "oec_manifest_id": oec["corpus_manifest"]["manifest_id"],
        "oec_manifest_hash": oec["corpus_manifest"]["manifest_hash"],
        "dtx_manifest_id": dtx_manifest["manifest_id"],
        "dtx_manifest_hash": dtx_manifest["manifest_hash"],
        "explicit_manifest_only": True,
    }


def _component_replay_status(root: Path) -> dict:
    dib_verdict, dib_proof, _ = latest_gate_result(root, "DIB-DOCUMENT-INTAKE-BOUNDARY-CONSOLIDATION")
    oes_verdict, oes_proof, _ = latest_gate_result(root, "OES-OPERATOR-EVIDENCE-SOAK-CONSOLIDATION")
    dtx_verdict, dtx_proof, _ = latest_gate_result(root, "DTX-SAFE-TEXT-DOCUMENT-EXCHANGE-CONSOLIDATION")
    return {
        "dib_replay_status": {
            "proof_root": "DIB-DOCUMENT-INTAKE-BOUNDARY-CONSOLIDATION",
            "gate_verdict": dib_verdict,
            "proof_bundle": dib_proof,
            "is_green": dib_verdict.startswith("GREEN"),
        },
        "oes_replay_status": {
            "proof_root": "OES-OPERATOR-EVIDENCE-SOAK-CONSOLIDATION",
            "gate_verdict": oes_verdict,
            "proof_bundle": oes_proof,
            "is_green": oes_verdict.startswith("GREEN"),
        },
        "dtx_replay_status": {
            "proof_root": "DTX-SAFE-TEXT-DOCUMENT-EXCHANGE-CONSOLIDATION",
            "gate_verdict": dtx_verdict,
            "proof_bundle": dtx_proof,
            "is_green": dtx_verdict.startswith("GREEN"),
        },
    }


def run_rc_soak(root: Path, *, iteration_count: int = RC_SOAK_ITERATION_COUNT) -> dict:
    manifest_refs = _explicit_manifest_refs(root)
    dtx_soak = run_dtx_document_soak(root, iteration_count=iteration_count)
    baseline = dtx_soak["baseline_layer"]
    expected_hash = rc_stable_hash(
        {
            "manifest_refs": manifest_refs,
            "dtx_stable_hash": baseline["stable_hash"],
            "component_replay": _component_replay_status(root),
        }
    )
    iterations = []
    for i in range(1, iteration_count + 1):
        layer = run_dtx_pipeline(root)
        current_hash = rc_stable_hash(
            {
                "manifest_refs": manifest_refs,
                "dtx_stable_hash": layer["stable_hash"],
                "component_replay": _component_replay_status(root),
            }
        )
        match = current_hash == expected_hash
        iterations.append(
            build_rc_soak_iteration(
                iteration_id=f"sle-rc-iter-{i:03d}",
                iteration_number=i,
                stable_hash=current_hash,
                replay_match=match,
            )
        )
    mutation = build_rc_mutation_summary(baseline_layer=baseline, expected_hash=expected_hash)
    manifest = build_rc_soak_manifest(
        manifest_id="sle-rc-soak-manifest-v1",
        iteration_count=iteration_count,
        oec_manifest_ref=manifest_refs["oec_manifest_id"],
        dtx_manifest_ref=manifest_refs["dtx_manifest_id"],
    )
    stable_hashes = {
        "expected_hash": expected_hash,
        "iteration_hashes": [row["stable_hash"] for row in iterations],
        "stable_hash_record_hash": record_hash({"hashes": [row["stable_hash"] for row in iterations]}),
    }
    replay_result = {
        "iteration_count": iteration_count,
        "all_iterations_match": all(row["replay_match"] for row in iterations),
        "replay_deterministic": all(row["replay_match"] for row in iterations),
        "component_replay_status": _component_replay_status(root),
        "mutation_mismatch_detected": mutation["mutation_mismatch_detected"],
        "mutation_auto_repaired": False,
        **neutral_flags(),
    }
    assert_neutral(replay_result)
    return {
        "rc_soak_manifest": manifest,
        "rc_soak_iterations": iterations,
        "rc_stable_hashes": stable_hashes,
        "rc_replay_result": replay_result,
        "rc_mutation_summary": mutation,
        "manifest_refs": manifest_refs,
        "dtx_baseline_layer": baseline,
    }
