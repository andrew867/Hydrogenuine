"""Receipt hash-chain enforcement tests (morning hardening tranche) — 10 required cases.

Run: python -m pytest --import-mode=importlib -q tests/receipt_hash_chain
Covers both the canonical open checker (hydrogenuine-proofkit) and the hardened
runtime journal validator. Assertions read JSON verdicts, never exit codes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
OUTER = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(OUTER / "hydrogenuine-proofkit" / "tools"))

try:
    from _common import receipt_hash  # noqa: E402
    from receipt_hash_chain_checker import check_chain, check_jsonl  # noqa: E402
except ModuleNotFoundError:
    pytest.skip("external hydrogenuine-proofkit tooling not checked out",
                allow_module_level=True)
from hg_runtime.agent_zero_state.turn_journal import TurnJournal, TurnJournalError  # noqa: E402
from hg_runtime.agent_zero_state.turn_receipt import build_turn_receipt  # noqa: E402
from hg_runtime.agent_zero_state.types import TurnReceiptVerdict  # noqa: E402


def _receipt(i: int, prev: str | None, **over) -> dict:
    r = {"receipt_id": f"r-{i}", "turn_index": i, "agent_id": "a1", "run_id": "run-1",
         "payload": f"turn {i} work", "previous_turn_hash": prev}
    r.update(over)
    r["hash"] = receipt_hash(r)
    return r


def _chain(n: int = 3) -> list[dict]:
    out, prev = [], None
    for i in range(1, n + 1):
        r = _receipt(i, prev)
        out.append(r)
        prev = r["hash"]
    return out


# 1. Valid chain passes
def test_valid_three_turn_chain_green():
    rep = check_chain(_chain(3))
    assert rep["verdict"] == "GREEN_RECEIPT_CHAIN_VALID"
    assert rep["checked"] == 3 and not rep["failures"]


# 2. Missing previous hash fails when required
def test_missing_previous_hash_after_first_turn_red():
    c = _chain(3)
    c[2] = _receipt(3, None)
    rep = check_chain(c)
    assert rep["verdict"] == "RED_RECEIPT_CHAIN_INVALID"
    assert any(f["code"] == "MISSING_PREVIOUS_HASH" for f in rep["failures"])


# 3. Wrong previous hash fails
def test_wrong_previous_hash_red():
    c = _chain(3)
    c[1] = _receipt(2, "sha256:" + "0" * 64)
    rep = check_chain(c)
    assert any(f["code"] == "WRONG_PREVIOUS_HASH" for f in rep["failures"])


# 4. Tampered prior receipt (stale hash field) fails — the key regression
def test_tampered_prior_entry_stale_hash_red():
    c = _chain(3)
    c[0]["payload"] = "history rewritten"  # hash field left stale
    rep = check_chain(c)
    assert any(f["code"] == "TAMPERED_ENTRY" and f["index"] == 0 for f in rep["failures"])


# 5. Out-of-order chain fails (order is material)
def test_out_of_order_turn_index_red():
    c = _chain(3)
    c[2]["turn_index"] = 7
    c[2]["hash"] = receipt_hash(c[2])
    # relink so ONLY the order violation fires
    rep = check_chain(c)
    assert any(f["code"] == "OUT_OF_ORDER" for f in rep["failures"])


# 6. Explicitly unchained receipt allowed only when labelled
def test_unchained_receipt_labelled_ok_unlabeled_red():
    c = _chain(2)
    c.insert(1, {"receipt_id": "side-note", "unchained": True, "note": "advisory"})
    rep = check_chain(c)
    assert rep["verdict"] == "GREEN_RECEIPT_CHAIN_VALID", rep["failures"]
    # unlabeled receipt without hash/link fails closed
    c2 = _chain(2)
    c2.insert(1, {"receipt_id": "sneaky", "note": "no label, no hash"})
    rep2 = check_chain(c2)
    assert rep2["verdict"] == "RED_RECEIPT_CHAIN_INVALID"


# 7. Canonical hash is deterministic
def test_canonical_hash_deterministic():
    a = {"z": 1, "a": [1, 2], "m": {"k": "v"}}
    assert receipt_hash(dict(a)) == receipt_hash(dict(reversed(list(a.items()))))


# 8. Validator ignores non-semantic formatting (whitespace/key order in JSONL)
def test_hash_insensitive_to_json_formatting(tmp_path):
    c = _chain(2)
    pretty = "\n".join(json.dumps(r, indent=None, sort_keys=False) for r in c)
    ugly = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in c)
    p1, p2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    p1.write_text(pretty, encoding="utf-8")
    p2.write_text(ugly, encoding="utf-8")
    assert check_jsonl(p1)["verdict"] == check_jsonl(p2)["verdict"] == "GREEN_RECEIPT_CHAIN_VALID"


# 9. Validator never rewrites the target (sealed-bundle safety)
def test_validator_never_rewrites_input(tmp_path):
    p = tmp_path / "chain.jsonl"
    content = "\n".join(json.dumps(r) for r in _chain(2))
    p.write_text(content, encoding="utf-8")
    before = p.read_bytes()
    check_jsonl(p)
    assert p.read_bytes() == before


# 10. Runtime journal: hardened verify_chain catches tamper + genesis + order
def test_journal_hardened_verification(tmp_path):
    j = TurnJournal(path=tmp_path / "turn_journal.jsonl")
    prev = None
    for i in range(1, 4):
        _, r = build_turn_receipt(
            agent_id="a1", turn_index=i, runtime_mode="fixture",
            observe_snapshot_ref=f"obs-{i}", capability_menu_ref=f"menu-{i}",
            chosen_action="witness_turn", previous_turn_hash=prev, run_id="run-1")
        j.append(r)
        prev = r.hash
    rep = j.verify_chain_report()
    assert rep["verdict"] == "GREEN_TURN_CHAIN_VALID", rep["failures"]

    # tamper an entry's payload, keep stale hash: must now be detected
    lines = j.path.read_text(encoding="utf-8").splitlines()
    e = json.loads(lines[0])
    e["chosen_action"] = "publish_everything"
    lines[0] = json.dumps(e, sort_keys=True, separators=(",", ":"))
    j.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rep2 = j.verify_chain_report()
    assert any(f["code"] == "TAMPERED_ENTRY" for f in rep2["failures"])
    with pytest.raises(TurnJournalError):
        j.verify_chain()


# 10b. Policy enforcement: null previous hash after first turn is RED at build time
def test_policy_enforced_null_prev_after_first_turn():
    verdict, _ = build_turn_receipt(
        agent_id="a1", turn_index=2, runtime_mode="fixture",
        observe_snapshot_ref="obs", capability_menu_ref="menu",
        chosen_action="witness_turn", previous_turn_hash=None)
    assert verdict == TurnReceiptVerdict.RED_TURN_CHAIN_BROKEN
    # genesis (turn 1) with null prev remains valid
    verdict2, _ = build_turn_receipt(
        agent_id="a1", turn_index=1, runtime_mode="fixture",
        observe_snapshot_ref="obs", capability_menu_ref="menu",
        chosen_action="witness_turn", previous_turn_hash=None)
    assert verdict2 != TurnReceiptVerdict.RED_TURN_CHAIN_BROKEN
