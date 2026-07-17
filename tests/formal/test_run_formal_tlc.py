"""TLC runner tests (FCP tranche) — fail-closed behavior.

Run: python -m pytest --import-mode=importlib -q tests/formal/test_run_formal_tlc.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "scripts"))

import run_formal_tlc as R  # noqa: E402


# 1. Runner fails closed when jar/tool missing (with --require-tlc)
def test_runner_fails_closed_when_tool_missing(monkeypatch):
    monkeypatch.setattr(R, "find_tlc", lambda: None)
    monkeypatch.setattr(sys, "argv", ["run_formal_tlc.py", "--require-tlc"])
    assert R.main() == 1
    # without --require-tlc: honest skip, exit 0
    monkeypatch.setattr(sys, "argv", ["run_formal_tlc.py"])
    assert R.main() == 0


# 2. Parser fails closed on malformed/incomplete output
def test_parser_fails_closed_on_malformed_output():
    r = R.parse_tlc_output("garbage output, no completion marker", "", 0)
    assert r["verdict"] == "RED_TLC_INCOMPLETE_OR_UNPARSEABLE"
    r2 = R.parse_tlc_output("Was expecting module body", "", 255)
    assert r2["verdict"] == "RED_TLC_PARSE_ERROR"
    # completed but unexplained nonzero exit is still a failure
    r3 = R.parse_tlc_output("Model checking completed. 5 states generated, 3 distinct states found", "", 3)
    assert r3["verdict"] == "RED_TLC_UNEXPLAINED_NONZERO"


# 2b. Violations are recorded, never masked
def test_parser_records_violations():
    out = ("Error: Invariant SG2_HumanDominance is violated.\n"
           "Model checking completed. 174 states generated, 97 distinct states found")
    r = R.parse_tlc_output(out, "", 12)
    assert r["verdict"] == "RED_INVARIANT_VIOLATED"
    assert r["invariant_violated"] == "SG2_HumanDominance"
    assert r["states"] == {"generated": 174, "distinct": 97}


# 2c. Clean completion passes only with exit 0
def test_parser_green_requires_completion_and_zero_exit():
    out = "Model checking completed. 949 states generated, 128 distinct states found"
    assert R.parse_tlc_output(out, "", 0)["verdict"] == "GREEN_INVARIANTS_HELD_BOUNDED"


# 3. FORMAL_STATUS cannot claim RUN/PASS without a result file
def test_formal_status_run_rows_have_receipts():
    text = (WORKSPACE / "docs" / "FORMAL_STATUS.md").read_text(encoding="utf-8")
    if "RUN RECORDED" in text:
        import re
        m = re.search(r"docs/proofs/formal_tlc/(\d{8}T\d{6}Z)/", text)
        assert m, "RUN RECORDED rows must cite a formal_tlc receipt bundle path"
        bundle = WORKSPACE / "docs" / "proofs" / "formal_tlc" / m.group(1)
        assert (bundle / "formal_tlc_result.json").is_file()
        result = json.loads((bundle / "formal_tlc_result.json").read_text(encoding="utf-8"))
        assert result["models_completed"] >= 1


# 4. CI status cannot claim enforced without config evidence
def test_ci_status_requires_config_evidence():
    text = (WORKSPACE / "docs" / "FORMAL_STATUS.md").read_text(encoding="utf-8")
    gitlab = (WORKSPACE / ".gitlab-ci.yml").read_text(encoding="utf-8") \
        if (WORKSPACE / ".gitlab-ci.yml").is_file() else ""
    tlc_in_gitlab = "run_formal_tlc" in gitlab and "--require-tlc" in gitlab
    if not tlc_in_gitlab:
        assert "NOT CI-ENFORCED" in text, \
            "FORMAL_STATUS must say NOT CI-ENFORCED while no required CI TLC job exists"
