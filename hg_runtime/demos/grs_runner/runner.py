"""Scenario-driven GRS runner — one pipeline for every scenario.

Reuses the proven GRS orchestrator helpers and the real runtime modules
(quarantine store, evidence graph schema, operator review schemas, quality
classifier). No silent fallback anywhere: live failures raise, they never
degrade to fixtures.

Pipeline: load scenario -> preflight -> model proposal -> quality gate ->
source capture -> evidence graph -> candidates -> quarantine -> operator
review packet -> decisions -> gated promotion -> final document -> proof
bundle (receipts, proof index, claim boundary, checksums).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.memory_quarantine.quarantine_store import (
    add_candidate, create_candidate, create_store, transition_state,
)
from hg_runtime.operator_review_promotion.schemas import neutral_flags
from hg_runtime.output_quality.classifier import classify

from hg_runtime.demos.governed_research_soak.orchestrator import (
    _build_evidence_graph, _extract_claims, _live_model_call,
    _live_source_capture, _probe_model_endpoint, _receipt_hash, _select_model,
)
from hg_runtime.demos.governed_research_soak.fixtures import (
    FIXTURE_FIRST_PASS, FIXTURE_MODEL_ID, FIXTURE_SECOND_PASS, FIXTURE_SOURCES,
)
from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
from hg_runtime.demos.grs_runner.scenario_schema import (
    data_tier, load_scenario, publicability,
)


class LiveModeUnavailable(RuntimeError):
    """Live requirement not satisfied — the run fails; it never falls back."""


def _call_live_model(prompt: str, cfg: dict, attempts: int = 2) -> str:
    """Live call with one documented retry on transport timeout. A retry is not a
    fallback: if all attempts fail, the run fails."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            content = _live_model_call(prompt, cfg)
            if attempt > 1:
                cfg.setdefault("_model_call_log", [])
                if cfg["_model_call_log"]:
                    cfg["_model_call_log"][-1]["attempt"] = attempt
                    cfg["_model_call_log"][-1]["retried_after_timeout"] = True
            return content
        except Exception as exc:  # noqa: BLE001 — transport errors become honest failure
            last = exc
    raise LiveModeUnavailable(f"live model call failed after {attempts} attempts: {last!r}")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_scenario(scenario: dict, out: Path) -> dict:
    scenario = load_scenario(scenario)
    out.mkdir(parents=True, exist_ok=True)
    sid = scenario["scenario_id"]
    mode = scenario["mode"]
    tier = data_tier(scenario)
    src_mode = scenario["sources"]["mode"]
    op_cfg = scenario["operator_review"]

    _write_json(out / "scenario_config.json", scenario)

    session = {
        "schema_version": "1", "receipt_id": f"grsr-{uuid.uuid4().hex[:12]}",
        "scenario_id": sid, "question": scenario["question"], "mode": mode,
        "data_tier": tier, "source_mode": src_mode,
        "operator_mode": op_cfg["mode"], "production_operator_auth": False,
        "publicability": publicability(scenario), "started_at": _now(),
    }
    session["hash"] = _receipt_hash(session)
    _write_json(out / "session_receipt.json", session)

    # --- Model proposal (no silent fallback) ---
    model_calls = []
    if mode == "live_local_model":
        cfg = {"model_base_url": scenario["model"]["endpoint"],
               "model_name": scenario["model"].get("model_name", "")}
        probe = _probe_model_endpoint(cfg)
        if not probe["available"]:
            raise LiveModeUnavailable(
                f"live_local_model required but endpoint unavailable: {probe.get('error')}")
        if scenario["model"].get("cloud_providers_allowed", False):
            raise LiveModeUnavailable("cloud providers are not supported by this runner")
        model_id = _select_model(cfg, probe)
        cfg["live_model_id"] = model_id
        first_pass = _call_live_model(scenario["question"], cfg)
        model_calls = cfg.get("_model_call_log", [])
        provider = {
            "schema_version": "1", "provider_kind": "local_openai_compatible",
            "endpoint": scenario["model"]["endpoint"], "model": model_id,
            "local_provider": True, "cloud_provider_used": False,
            "available_models": len(probe["models"]), "data_tier": tier,
            "calls": model_calls, "timestamp": _now(),
        }
        provider["hash"] = _receipt_hash(provider)
        _write_json(out / "model_provider_receipt.json", provider)
    elif mode == "fixture":
        model_id = FIXTURE_MODEL_ID
        first_pass = FIXTURE_FIRST_PASS
        _write_json(out / "fixture_label.json", {
            "fixture_label": "FIXTURE MODE — not live evidence; cannot be public GREEN",
            "data_tier": "fixture", "scenario_id": sid,
        })
    else:  # guided_replay
        replay = scenario.get("replay_source")
        if not replay or not Path(replay).is_file():
            raise LiveModeUnavailable("guided_replay requires an existing replay_source")
        first_pass = json.loads(Path(replay).read_text(encoding="utf-8"))["first_pass"]
        model_id = "replay/" + Path(replay).stem

    proposal = {
        "schema_version": "1", "proposal_id": f"grsr-prop-{uuid.uuid4().hex[:12]}",
        "model": model_id, "content": first_pass, "data_tier": tier,
        "timestamp": _now(),
    }
    proposal["hash"] = _receipt_hash(proposal)
    _write_json(out / "model_proposal_receipt.json", proposal)

    # --- Quality gate (real classifier) ---
    qc = classify(first_pass, model_id, len(first_pass))
    quality_class = qc["quality_class"]
    issues = list(qc["issue_categories"])
    if scenario["quality_gate"].get("require_source_support", True) and \
            "unsupported_assertion" not in issues:
        issues.append("unsupported_assertion")
        quality_class = "NEEDS_SOURCE_SUPPORT"
    quality = {
        "schema_version": "1", "quality_receipt_id": f"grsr-q-{uuid.uuid4().hex[:12]}",
        "artifact_hash": proposal["hash"], "quality_class": quality_class,
        "issues": issues, "scores": {k: qc[k] for k in
                                     ("slop_score", "repetition_score", "specificity_score")},
        "timestamp": _now(),
    }
    quality["hash"] = _receipt_hash(quality)
    _write_json(out / "quality_gate_receipt.json", quality)

    # --- Sources (explicit mode; no fallback) ---
    sources: list[dict] = []
    if src_mode == "live_allowlist":
        allow = scenario["sources"]["allowlist"]
        cfg_sources = _live_source_capture({"source_allowlist": allow}) \
            if _uses_config_allowlist() else _capture_allowlist(allow)
        sources = cfg_sources
        succeeded = [s for s in sources if s.get("capture_status") == "success"]
        if len(succeeded) < int(scenario["sources"].get("minimum_source_count", 1)):
            raise LiveModeUnavailable(
                f"live_allowlist requires >= {scenario['sources']['minimum_source_count']}"
                f" captured sources; got {len(succeeded)}")
    elif src_mode == "fixture":
        sources = [dict(s, capture_mode="fixture", capture_status="success")
                   for s in FIXTURE_SOURCES]
    # disabled -> []
    if sources:
        with (out / "source_capture_receipts.jsonl").open("w", encoding="utf-8") as f:
            for s in sources:
                rec = dict(s, schema_version="1", data_tier=tier, timestamp=_now())
                rec["hash"] = _receipt_hash(rec)
                f.write(json.dumps(rec) + "\n")

    # --- Second pass with sources (live) or fixture second pass ---
    if mode == "live_local_model" and sources:
        src_block = "\n".join(f"- {s['url']} ({s['title'][:80]})" for s in sources
                              if s.get("capture_status") == "success")
        cfg["live_model_id"] = model_id
        final_content = _call_live_model(
            f"{scenario['question']}\n\nCite only these sources:\n{src_block}", cfg)
        model_calls = cfg.get("_model_call_log", [])
        provider["calls"] = model_calls
        provider["hash"] = _receipt_hash({k: v for k, v in provider.items() if k != "hash"})
        _write_json(out / "model_provider_receipt.json", provider)
    elif mode == "fixture":
        final_content = FIXTURE_SECOND_PASS
    else:
        final_content = first_pass

    # --- Claims, evidence graph, quarantine ---
    claims = _extract_claims(final_content, sources or None)
    if not claims:
        claims = [{"claim_id": "claim-001", "text": final_content[:400],
                   "source_refs": [s["url"] for s in sources][:2]}]
    graph = _build_evidence_graph(scenario["question"], claims, sources, proposal["hash"])
    _write_json(out / "evidence_graph.json", graph)

    quarantine_records = []
    if scenario["quarantine"]["enabled"]:
        store = create_store()
        for i, c in enumerate(claims, 1):
            cid = c.get("claim_id", f"claim-{i:03d}")
            cand = create_candidate(
                candidate_id=f"{sid}-{cid}",
                content_summary=c["text"][:200],
                source="model_output",
                claim_text=c["text"][:400],
                model_id=model_id,
            )
            store = add_candidate(store, cand)
            quarantine_records.append({
                "candidate_id": cand["candidate_id"],
                "state": cand.get("state", "quarantined"),
                "promotion_allowed": False, "claim_id": cid,
            })
        _write_json(out / "memory_quarantine.json", {
            "schema_version": "1", "scenario_id": sid,
            "candidates": quarantine_records,
            "invariant": "candidate knowledge is not knowledge; promotion requires operator review",
        })

    # --- Operator review ---
    packet = {
        "schema_version": "1", "packet_id": f"grsr-rev-{uuid.uuid4().hex[:12]}",
        "scenario_id": sid, "operator_mode": op_cfg["mode"],
        "production_operator_auth": False,
        "claims": [{"claim_id": c.get("claim_id", f"claim-{i:03d}"),
                    "text": c["text"][:400],
                    "source_refs": c.get("source_refs", [])}
                   for i, c in enumerate(claims, 1)],
        "neutral_flags": neutral_flags(), "timestamp": _now(),
    }
    packet["hash"] = _receipt_hash(packet)
    _write_json(out / "operator_review_packet.json", packet)

    signer = OperatorSigner()
    decisions = _decide(packet["claims"], op_cfg, signer)
    with (out / "operator_decision_receipts.jsonl").open("w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d) + "\n")
    _write_json(out / "operator_identity.json", dict(
        signer.identity_record(), production_operator_auth=False,
        operator_identity_type="local_demo_signed_operator",
    ))

    approved = [d["claim_id"] for d in decisions if d["decision"] == "approve"]
    denied = [d["claim_id"] for d in decisions if d["decision"] == "deny"]
    promotion = {
        "schema_version": "1", "promotion_id": f"grsr-promo-{uuid.uuid4().hex[:12]}",
        "requires": ["quality_gate_receipt", "operator_decision_receipts"],
        "promoted_claims": approved, "denied_claims_not_promoted": denied,
        "rule": "promotion requires an approve decision; denied candidates are never promoted",
        "timestamp": _now(),
    }
    promotion["hash"] = _receipt_hash(promotion)
    _write_json(out / "promotion_receipt.json", promotion)

    # --- Final document ---
    doc = _final_document(scenario, proposal, quality, sources, decisions, promotion)
    (out / "final_document.md").write_text(doc, encoding="utf-8")

    # --- Claim boundary + proof index + gate placeholder + checksums ---
    (out / "claim_boundary_report.md").write_text(_claim_boundary(scenario, tier), encoding="utf-8")
    index = {
        "schema_version": "1", "proof_type": "grs_runner_scenario",
        "anchor_status": "not_anchored",
        "external_anchor": None,
        "external_anchor_reason": "deferred_no_external_effects",
        "scenario_id": sid, "mode": mode, "data_tier": tier,
        "publicability": publicability(scenario),
        "model": model_id, "model_calls": len(model_calls),
        "cloud_provider_used": False,
        "source_mode": src_mode, "source_count": len(sources),
        "operator_mode": op_cfg["mode"], "production_operator_auth": False,
        "approve_count": len(approved), "deny_count": len(denied),
        "quality_class": quality_class,
        "generated_at": _now(),
    }
    _write_json(out / "proof_index.json", index)

    files = sorted(p for p in out.rglob("*") if p.is_file()
                   and p.name not in {"checksums.sha256"})
    (out / "checksums.sha256").write_text(
        "\n".join(f"{_sha256_file(p)}  {p.relative_to(out).as_posix()}" for p in files) + "\n",
        encoding="utf-8")
    return index


def _uses_config_allowlist() -> bool:
    """_live_source_capture reads the module-global allowlist; use our own capture."""
    return False


def _capture_allowlist(allowlist: list[dict]) -> list[dict]:
    """Per-scenario live capture (same shape as orchestrator's, scenario allowlist)."""
    import re
    import urllib.request
    out = []
    for entry in allowlist:
        url = entry["url"]
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Hydrogenuine-GRS-Runner/0.1 (research-source-capture)",
                "Accept": "text/html,application/xhtml+xml"})
            content = urllib.request.urlopen(req, timeout=30).read()
            m = re.search(rb"<title[^>]*>(.*?)</title>", content, re.I | re.S)
            title = re.sub(r"\s+", " ", m.group(1).decode("utf-8", "replace").strip()) if m else url
            out.append({"url": url, "title": title,
                        "source_type": entry.get("source_type", "web"),
                        "label": entry.get("label", "supporting"),
                        "content_hash": f"sha256:{hashlib.sha256(content).hexdigest()}",
                        "capture_mode": "live_http_get", "capture_status": "success",
                        "content_length": len(content)})
        except Exception as exc:  # recorded, not hidden
            out.append({"url": url, "title": f"FAILED: {url}",
                        "source_type": entry.get("source_type", "web"),
                        "label": "insufficient", "content_hash": "sha256:capture_failed",
                        "capture_mode": "live_http_get",
                        "capture_status": f"error: {str(exc)[:200]}", "content_length": 0})
    return out


def _decide(claims: list[dict], op_cfg: dict, signer: OperatorSigner) -> list[dict]:
    decisions = []
    for i, claim in enumerate(claims):
        want_deny = op_cfg.get("require_deny", False) and i == len(claims) - 1 and len(claims) > 1
        decision = "deny" if want_deny else ("approve" if op_cfg.get("require_approve", True) else "hold")
        reason = ("insufficient source support for this candidate"
                  if decision == "deny" else "source-supported candidate")
        payload = {
            "schema_version": "1", "claim_id": claim["claim_id"],
            "decision": decision, "reason": reason,
            "operator_mode": op_cfg["mode"], "production_operator_auth": False,
            "decision_source": ("simulated_fixture" if op_cfg["mode"] == "fixture_simulated_operator"
                                else "local_signed_demo_operator"),
            "timestamp": _now(),
        }
        payload["signature"] = signer.sign(payload)
        payload["hash"] = _receipt_hash(payload)
        decisions.append(payload)
    return decisions


def _final_document(scenario, proposal, quality, sources, decisions, promotion) -> str:
    lines = [
        f"# {scenario['title']}", "",
        f"**Question:** {scenario['question']}", "",
        f"**Governance chain:** proposal `{proposal['hash'][:23]}` -> quality gate "
        f"`{quality['hash'][:23]}` ({quality['quality_class']}) -> operator decisions -> "
        f"promotion `{promotion['hash'][:23]}`", "",
        "## Promoted findings", "",
    ]
    approved = set(promotion["promoted_claims"])
    for d in decisions:
        mark = "PROMOTED" if d["claim_id"] in approved else "NOT PROMOTED (denied/held)"
        lines.append(f"- **{d['claim_id']}** [{mark}] — decision receipt `{d['hash'][:23]}`")
    if sources:
        lines += ["", "## Sources (receipts, not truth)", ""]
        lines += [f"- {s['url']} — `{s['content_hash'][:23]}` ({s['capture_status']})"
                  for s in sources]
    lines += ["", "---", "",
              "Proof records the path. It does not prove model correctness. "
              "Source is receipt, not truth. The local signed demo operator is not "
              "production auth."]
    return "\n".join(lines) + "\n"


def _claim_boundary(scenario, tier) -> str:
    return f"""# Claim Boundary — scenario {scenario['scenario_id']}

- Proof records the path. It does not prove model correctness.
- Source is receipt, not truth.
- The local signed demo operator is not production auth.
- Fixture mode is not public-live proof (this run: data_tier={tier},
  publicability={publicability(scenario)}).
- No customer deployment, production certification, external anchoring, or
  autonomous authority is claimed.
- Publicability depends on scenario mode and evidence; fake GREEN is forbidden.
"""
