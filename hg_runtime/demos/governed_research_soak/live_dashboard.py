"""Generate a self-contained dashboard HTML for the live recorded GRS run.

Uses the Hydrogenuine design system tokens (colors, typography, spacing, effects)
inlined so the page renders without external dependencies beyond Google Fonts.
"""

from __future__ import annotations

import json
from pathlib import Path
from html import escape


def _read_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl(path: Path) -> list[dict]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").strip().split("\n") if line.strip()]
    except Exception:
        return []


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _badge(text: str, tone: str = "pending") -> str:
    colors = {
        "allowed": ("var(--hg-green)", "var(--hg-green-dim)", "var(--hg-green-line)"),
        "pending": ("var(--hg-amber)", "var(--hg-amber-dim)", "var(--hg-amber-line)"),
        "evidence": ("var(--hg-blue)", "var(--hg-blue-dim)", "var(--hg-blue-line)"),
        "refused": ("var(--hg-red)", "var(--hg-red-dim)", "var(--hg-red-line)"),
        "quarantine": ("var(--hg-violet)", "var(--hg-violet-dim)", "var(--hg-violet-line)"),
    }
    fg, bg, border = colors.get(tone, colors["pending"])
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:var(--radius-xs);'
        f'font-family:var(--font-mono);font-size:11px;font-weight:600;letter-spacing:0.06em;'
        f'color:{fg};background:{bg};border:1px solid {border}">{escape(text)}</span>'
    )


def _hash_display(h: str) -> str:
    if not h:
        return ""
    short = h[:20] + "..." + h[-8:] if len(h) > 32 else h
    return f'<span class="hg-hash">{escape(short)}</span>'


def _meta_row(key: str, value: str, accent: str = "") -> str:
    color = f"var(--hg-{accent})" if accent else "var(--hg-muted)"
    return (
        f'<div style="display:flex;justify-content:space-between;gap:16px;padding:6px 0;'
        f'border-bottom:1px solid var(--hg-border-soft)">'
        f'<span style="font-family:var(--font-mono);font-size:12px;color:var(--hg-faint)">{escape(key)}</span>'
        f'<span style="font-family:var(--font-mono);font-size:12px;color:{color};text-align:right;'
        f'word-break:break-all">{escape(str(value))}</span></div>'
    )


def _stage_card(num: int, title: str, badge_text: str, badge_tone: str, content: str) -> str:
    return f"""
    <section id="stage-{num}" class="stage-card">
      <div class="stage-header">
        <div class="stage-num">{num:02d}</div>
        <div class="stage-title-block">
          <h3>{escape(title)}</h3>
          <div style="margin-top:4px">{_badge(badge_text, badge_tone)}</div>
        </div>
      </div>
      <div class="stage-body">{content}</div>
    </section>"""


def generate_live_dashboard(bundle_dir: str | Path) -> str:
    """Generate a self-contained HTML dashboard from a proof bundle directory."""
    bd = Path(bundle_dir)

    config = _read_json(bd / "demo_config.json") or {}
    session = _read_json(bd / "session_receipt.json") or {}
    provider = _read_json(bd / "local_model_provider_receipt.json") or {}
    proposal = _read_json(bd / "model_proposal_receipt.json") or {}
    quality = _read_json(bd / "quality_gate_receipt.json") or {}
    hold = _read_json(bd / "refusal_or_hold_receipt.json") or {}
    sources = _read_jsonl(bd / "source_capture_receipts.jsonl")
    evidence = _read_json(bd / "evidence_graph.json") or {}
    quarantine = _read_json(bd / "memory_quarantine.json") or {}
    review = _read_json(bd / "operator_review_packet.json") or {}
    decision = _read_json(bd / "operator_decision_receipt.json") or {}
    promotion = _read_json(bd / "promotion_receipt.json") or {}
    manifest = _read_json(bd / "manifest.json") or {}
    final_answer = _read_text(bd / "final_answer.md")
    claim_report = _read_text(bd / "claim_boundary_report.md")
    checksums = _read_text(bd / "checksums.sha256")

    session_id = session.get("session_id", manifest.get("bundle_id", "unknown"))
    verdict = manifest.get("verdict", "UNKNOWN")
    verdict_tone = "allowed" if verdict.startswith("GREEN") else "pending" if verdict.startswith("YELLOW") else "refused"
    model_name = provider.get("model_name", config.get("model_name", "unknown"))
    endpoint = provider.get("endpoint_base_url", config.get("model_base_url", "unknown"))
    data_tier = config.get("data_tier", "unknown")

    stages = []

    # 1 — Session start
    stages.append(_stage_card(1, "Session Start", "STARTED", "evidence",
        _meta_row("session_id", session_id, "blue")
        + _meta_row("started_at", session.get("started_at", ""), "blue")
        + _meta_row("demo_mode", str(config.get("demo_mode", True)))
        + _meta_row("data_tier", data_tier, "amber" if data_tier != "live" else "green")
        + _meta_row("hash", session.get("hash", ""), "blue")
    ))

    # 2 — Research question
    stages.append(_stage_card(2, "Research Question", "SUBMITTED", "evidence",
        f'<div style="font-family:var(--font-body);font-size:15px;color:var(--hg-text);'
        f'padding:14px;background:var(--hg-bg);border:1px solid var(--hg-border);'
        f'border-radius:var(--radius-sm);line-height:1.5">'
        f'&ldquo;{escape(session.get("question", ""))}&rdquo;</div>'
    ))

    # 3 — Local model endpoint
    model_badge = "LIVE LOCAL MODEL" if provider.get("local_provider") else "FIXTURE"
    model_tone = "allowed" if provider.get("local_provider") else "pending"
    first_call = provider.get("first_call", {})
    model_content = (
        _meta_row("endpoint", endpoint, "green")
        + _meta_row("model", model_name, "green")
        + _meta_row("local_provider", str(provider.get("local_provider", False)), "green")
        + _meta_row("cloud_provider", str(provider.get("cloud_provider", False)))
        + _meta_row("available_models", str(len(provider.get("available_models", []))))
    )
    if first_call:
        model_content += (
            _meta_row("first_call_latency", f'{first_call.get("latency_s", "?")}s', "blue")
            + _meta_row("tokens_used", str(first_call.get("usage", {}).get("total_tokens", "?")), "blue")
            + _meta_row("response_hash", first_call.get("response_hash", ""), "blue")
        )
    stages.append(_stage_card(3, "Local Model Endpoint", model_badge, model_tone, model_content))

    # 4 — First model proposal
    content_preview = proposal.get("content", "")[:500]
    stages.append(_stage_card(4, "First Model Proposal", "RECEIPT WRITTEN", "evidence",
        f'<div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-muted);'
        f'padding:12px;background:var(--hg-bg);border:1px solid var(--hg-border);'
        f'border-radius:var(--radius-sm);max-height:200px;overflow-y:auto;'
        f'white-space:pre-wrap;line-height:1.5">{escape(content_preview)}{"..." if len(proposal.get("content", "")) > 500 else ""}</div>'
        + _meta_row("pass_number", str(proposal.get("pass_number", 1)))
        + _meta_row("model_id", proposal.get("model_id", ""))
        + _meta_row("hash", proposal.get("hash", ""), "blue")
    ))

    # 5 — Quality gate
    qclass = quality.get("quality_class", "UNKNOWN")
    stages.append(_stage_card(5, "Quality Gate", qclass, "pending" if "NEEDS" in qclass else "allowed",
        _meta_row("quality_class", qclass, "amber")
        + _meta_row("issues", ", ".join(quality.get("issues", [])), "amber")
        + _meta_row("route", quality.get("route", ""), "amber")
        + _meta_row("slop_score", str(quality.get("scores", {}).get("slop_score", "")))
        + _meta_row("hash", quality.get("hash", ""), "blue")
    ))

    # 6 — Hold/refusal
    stages.append(_stage_card(6, "Hold / Refusal", "HELD", "refused",
        f'<div style="font-family:var(--font-body);font-size:14px;color:var(--hg-red);'
        f'padding:12px;background:var(--hg-red-dim);border:1px solid var(--hg-red-line);'
        f'border-radius:var(--radius-sm);margin-bottom:12px">'
        f'{escape(hold.get("reason", ""))}</div>'
        + _meta_row("action", hold.get("action", ""), "amber")
        + _meta_row("hash", hold.get("hash", ""), "blue")
    ))

    # 7 — Source capture
    source_cards = ""
    for i, src in enumerate(sources, 1):
        status = src.get("capture_status", "unknown")
        tone = "allowed" if status == "success" else "refused"
        source_cards += (
            f'<div style="padding:12px;background:var(--hg-bg);border:1px solid var(--hg-border);'
            f'border-radius:var(--radius-sm);margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint)">source-{i}</span>'
            f'{_badge(status.upper(), tone)}</div>'
            f'{_meta_row("url", src.get("url", ""), "blue")}'
            f'{_meta_row("title", src.get("title", "")[:60])}'
            f'{_meta_row("type", src.get("source_type", ""))}'
            f'{_meta_row("label", src.get("label", ""), "amber")}'
            f'{_meta_row("content_hash", src.get("content_hash", ""), "blue")}'
            f'{_meta_row("capture_mode", src.get("capture_mode", ""))}'
            f'{_meta_row("bytes", str(src.get("content_length", 0)))}'
            f'</div>'
        )
    capture_label = f"LIVE SOURCE CAPTURE ({sum(1 for s in sources if s.get('capture_status') == 'success')}/{len(sources)})"
    stages.append(_stage_card(7, "Source Capture", capture_label, "allowed" if sources else "refused", source_cards))

    # 8 — Evidence graph
    nodes = evidence.get("nodes", [])
    edges = evidence.get("edges", [])
    eg_content = f'<div style="margin-bottom:12px">{_meta_row("nodes", str(len(nodes)))}{_meta_row("edges", str(len(edges)))}</div>'
    for node in nodes:
        nt = node.get("node_type", "")
        tone = "evidence" if nt == "claim" else "allowed" if nt == "source_candidate" else "refused"
        eg_content += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
            f'border-bottom:1px solid var(--hg-border-soft)">'
            f'{_badge(nt, tone)}'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-muted)">'
            f'{escape(node.get("label", "")[:60])}</span></div>'
        )
    stages.append(_stage_card(8, "Evidence Graph", "GRAPH BUILT", "evidence", eg_content))

    # 9 — Memory quarantine
    entries = quarantine.get("entries", [])
    q_content = ""
    for e in entries:
        state = e.get("state", "unknown")
        tone = "allowed" if state == "promoted" else "quarantine" if state in ("quarantined", "deferred") else "pending"
        q_content += (
            f'<div style="padding:10px;background:var(--hg-bg);border:1px solid var(--hg-border);'
            f'border-radius:var(--radius-sm);margin-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint)">'
            f'{escape(e.get("candidate_id", ""))}</span>'
            f'{_badge(state.upper(), tone)}</div>'
            f'<div style="font-family:var(--font-body);font-size:13px;color:var(--hg-muted);line-height:1.4">'
            f'{escape(e.get("content_summary", "")[:100])}</div></div>'
        )
    invariants = ""
    for key in ("candidate_knowledge_is_not_knowledge", "promotion_requires_operator_review",
                "promotion_allowed", "model_output_treated_as_truth"):
        val = quarantine.get(key)
        if val is not None:
            invariants += _meta_row(key, str(val), "green" if key != "promotion_allowed" else "red")
    stages.append(_stage_card(9, "Memory Quarantine", "QUARANTINED", "quarantine", q_content + invariants))

    # 10 — Operator review
    stages.append(_stage_card(10, "Operator Review Packet", "REVIEWED", "pending",
        _meta_row("operator_mode", decision.get("operator_mode", ""), "amber")
        + _meta_row("operator_identity", decision.get("operator_identity", ""), "amber")
        + _meta_row("authenticated", str(decision.get("authenticated", False)), "red")
        + _meta_row("candidates", str(len(decision.get("decisions", []))))
        + _meta_row("hash", decision.get("hash", ""), "blue")
    ))

    # 11 — Operator decisions
    dec_content = ""
    for d in decision.get("decisions", []):
        status = d.get("status", "")
        tone = "allowed" if "APPROVE" in status else "quarantine" if "DEFER" in status else "refused"
        dec_content += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-bottom:1px solid var(--hg-border-soft)">'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint);min-width:70px">'
            f'{escape(d.get("candidate_ref", ""))}</span>'
            f'{_badge(status, tone)}'
            f'<span style="font-family:var(--font-body);font-size:12px;color:var(--hg-muted)">'
            f'{escape(d.get("reason", "")[:60])}</span></div>'
        )
    stages.append(_stage_card(11, "Operator Decisions", "simulated_local_demo_operator", "pending", dec_content))

    # 12 — Promotion receipt
    promo_content = (
        _meta_row("candidate_ref", promotion.get("candidate_ref", ""), "green")
        + _meta_row("provisional", str(promotion.get("provisional", "")), "amber")
        + _meta_row("operator_mode", promotion.get("operator_mode", ""), "amber")
    )
    chain = promotion.get("promotion_chain", [])
    if chain:
        promo_content += '<div style="margin-top:10px">'
        promo_content += '<div class="hg-eyebrow" style="margin-bottom:6px">promotion chain</div>'
        for j, step in enumerate(chain):
            arrow = " &rarr; " if j < len(chain) - 1 else ""
            promo_content += f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-blue)">{escape(step)}</span>{arrow}'
        promo_content += '</div>'
    promo_content += _meta_row("hash", promotion.get("hash", ""), "blue")
    stages.append(_stage_card(12, "Promotion Receipt", "PROMOTED", "allowed", promo_content))

    # 13 — Final answer
    answer_html = escape(final_answer[:1000]).replace("\n", "<br>")
    stages.append(_stage_card(13, "Final Answer", "RECEIPT WRITTEN", "evidence",
        f'<div style="font-family:var(--font-body);font-size:13px;color:var(--hg-text);'
        f'padding:14px;background:var(--hg-bg);border:1px solid var(--hg-border);'
        f'border-radius:var(--radius-sm);max-height:300px;overflow-y:auto;'
        f'line-height:1.6">{answer_html}{"..." if len(final_answer) > 1000 else ""}</div>'
    ))

    # 14 — Proof bundle manifest
    files = manifest.get("files", [])
    file_list = ""
    for f in files:
        file_list += (
            f'<div style="font-family:var(--font-mono);font-size:11px;color:var(--hg-muted);'
            f'padding:3px 0;border-bottom:1px solid var(--hg-border-soft)">{escape(f)}</div>'
        )
    stages.append(_stage_card(14, "Proof Bundle / Checksums", f"{len(files)} FILES", "evidence",
        _meta_row("bundle_id", manifest.get("bundle_id", ""))
        + _meta_row("verdict", verdict, "green" if verdict.startswith("GREEN") else "amber")
        + _meta_row("manifest_hash", manifest.get("hash", ""), "blue")
        + f'<div style="margin-top:12px"><div class="hg-eyebrow" style="margin-bottom:6px">file manifest</div>{file_list}</div>'
    ))

    # 15 — Claim boundary
    cb_status = "CLEAN" if "CLEAN" in claim_report else "VIOLATION"
    cb_tone = "allowed" if cb_status == "CLEAN" else "refused"
    stages.append(_stage_card(15, "Claim Boundary", cb_status, cb_tone,
        f'<div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-muted);'
        f'padding:12px;background:var(--hg-bg);border:1px solid var(--hg-border);'
        f'border-radius:var(--radius-sm);white-space:pre-wrap;line-height:1.5">'
        f'{escape(claim_report[:600])}</div>'
    ))

    # Sidebar nav
    nav_items = [
        (1, "Session"), (2, "Question"), (3, "Model"), (4, "Proposal"),
        (5, "Quality Gate"), (6, "Hold"), (7, "Sources"), (8, "Evidence"),
        (9, "Quarantine"), (10, "Review"), (11, "Decisions"), (12, "Promotion"),
        (13, "Answer"), (14, "Bundle"), (15, "Claims"),
    ]
    nav_html = ""
    for num, label in nav_items:
        nav_html += (
            f'<a href="#stage-{num}" class="nav-item">'
            f'<span class="nav-num">{num:02d}</span>{escape(label)}</a>\n'
        )

    # Ledger entries
    ledger_html = ""
    ledger_events = [
        ("session_start", session.get("started_at", ""), "evidence"),
        ("model_probed", provider.get("probe_timestamp", ""), "allowed"),
        ("first_pass", proposal.get("timestamp", ""), "evidence"),
        ("quality_hold", hold.get("timestamp", ""), "refused"),
        ("sources_captured", "3 URLs", "allowed"),
        ("quarantine", f"{len(entries)} candidates", "quarantine"),
        ("operator_review", decision.get("operator_mode", ""), "pending"),
        ("promotion", promotion.get("candidate_ref", ""), "allowed"),
        ("bundle_complete", f"{len(files)} files", "evidence"),
    ]
    for event, detail, tone in ledger_events:
        dot_color = {
            "allowed": "var(--hg-green)", "evidence": "var(--hg-blue)",
            "refused": "var(--hg-red)", "quarantine": "var(--hg-violet)",
            "pending": "var(--hg-amber)",
        }.get(tone, "var(--hg-faint)")
        ledger_html += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0;'
            f'font-family:var(--font-mono);font-size:11px">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{dot_color};flex-shrink:0"></span>'
            f'<span style="color:var(--hg-muted);min-width:120px">{escape(event)}</span>'
            f'<span style="color:var(--hg-faint)">{escape(str(detail)[:40])}</span></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hydrogenuine — Governed Research Soak · Live Recorded Run</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --hg-bg:#070A08;--hg-panel:#101512;--hg-card:#161C18;--hg-card-2:#1C231E;
  --hg-border:#29332D;--hg-border-soft:#1F2723;
  --hg-text:#F1EBDD;--hg-muted:#B8B2A4;--hg-faint:#6F7568;
  --hg-green:#8FE388;--hg-amber:#E6B35A;--hg-blue:#7FB7D8;--hg-red:#E06C75;--hg-violet:#9A8FBF;
  --hg-green-dim:#14241A;--hg-amber-dim:#261E12;--hg-blue-dim:#122029;--hg-red-dim:#271417;--hg-violet-dim:#1E1A26;
  --hg-green-line:#2D4F36;--hg-amber-line:#4D3D22;--hg-blue-line:#244456;--hg-red-line:#4D2A2E;--hg-violet-line:#3A3350;
  --font-display:'Space Grotesk',system-ui,sans-serif;
  --font-body:'Inter',system-ui,sans-serif;
  --font-mono:'IBM Plex Mono',ui-monospace,monospace;
  --radius-xs:3px;--radius-sm:5px;--radius-md:8px;
  --shadow-sm:0 1px 2px rgba(0,0,0,0.4);
  --inset-well:inset 0 1px 2px rgba(0,0,0,0.45);
}}
*,*::before,*::after {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0;background:var(--hg-bg);color:var(--hg-text);font-family:var(--font-body);font-size:15px;line-height:1.55; }}
h3 {{ font-family:var(--font-display);font-size:18px;font-weight:600;margin:0;letter-spacing:-0.01em; }}
.hg-eyebrow {{ font-family:var(--font-mono);font-size:11px;text-transform:uppercase;letter-spacing:0.16em;color:var(--hg-faint);font-weight:500; }}
.hg-hash {{ font-family:var(--font-mono);font-size:12px;color:var(--hg-blue);word-break:break-all; }}
::selection {{ background:rgba(45,79,54,0.6);color:var(--hg-text); }}
* {{ scrollbar-width:thin;scrollbar-color:var(--hg-border) transparent; }}

.console {{ display:flex;height:100vh; }}
.sidebar {{ width:220px;flex-shrink:0;background:var(--hg-panel);border-right:1px solid var(--hg-border);display:flex;flex-direction:column;height:100%; }}
.sidebar-logo {{ padding:18px 16px;border-bottom:1px solid var(--hg-border);display:flex;align-items:center;gap:10px; }}
.sidebar-logo .title {{ font-family:var(--font-display);font-size:14px;font-weight:600; }}
.sidebar-logo .sub {{ font-family:var(--font-mono);font-size:10px;color:var(--hg-faint);letter-spacing:0.08em; }}
.sidebar nav {{ flex:1;overflow-y:auto;padding:8px; }}
.nav-item {{ display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:var(--radius-sm);
  color:var(--hg-muted);font-family:var(--font-mono);font-size:12px;text-decoration:none;transition:background 120ms; }}
.nav-item:hover {{ background:var(--hg-card);color:var(--hg-text); }}
.nav-num {{ color:var(--hg-faint);min-width:20px; }}
.sidebar-status {{ padding:14px 16px;border-top:1px solid var(--hg-border); }}

.main {{ flex:1;display:flex;flex-direction:column;min-width:0; }}
.top-bar {{ display:flex;align-items:center;justify-content:space-between;padding:15px 24px;
  border-bottom:1px solid var(--hg-border);background:var(--hg-panel); }}
.top-bar h1 {{ font-family:var(--font-display);font-size:18px;font-weight:600;margin:0;letter-spacing:-0.01em; }}
.top-bar .meta {{ font-family:var(--font-mono);font-size:11px;color:var(--hg-faint);margin-top:2px; }}
.stages {{ flex:1;overflow-y:auto;padding:24px; }}
.stage-card {{ background:var(--hg-card);border:1px solid var(--hg-border);border-radius:var(--radius-md);
  margin-bottom:16px;overflow:hidden; }}
.stage-header {{ display:flex;align-items:flex-start;gap:14px;padding:16px 20px;border-bottom:1px solid var(--hg-border-soft);background:var(--hg-panel); }}
.stage-num {{ font-family:var(--font-mono);font-size:13px;color:var(--hg-faint);min-width:28px;padding-top:2px; }}
.stage-body {{ padding:16px 20px; }}

.ledger {{ border-top:1px solid var(--hg-border);background:var(--hg-panel);padding:12px 24px;max-height:160px;overflow-y:auto; }}

.disclaimer {{ position:fixed;left:0;right:0;top:0;z-index:999;font-family:var(--font-mono);font-size:11.5px;
  color:#cfe9c8;background:rgba(7,11,8,0.94);border-bottom:1px solid rgba(143,227,136,0.42);
  padding:7px 14px;text-align:center;letter-spacing:0.02em;backdrop-filter:blur(6px); }}
</style>
</head>
<body>
<div class="disclaimer" role="note">Live recorded demo. Local model. Simulated operator. Candidate knowledge is not knowledge. Receipt is not trust.</div>
<div class="console" style="padding-top:32px">
  <aside class="sidebar" style="padding-top:32px">
    <div class="sidebar-logo">
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
        <path d="M9 5H5.5A1.5 1.5 0 004 6.5V25.5A1.5 1.5 0 005.5 27H9" stroke="#6F7568" stroke-width="1.6" stroke-linecap="round"/>
        <path d="M23 5H26.5A1.5 1.5 0 0128 6.5V25.5A1.5 1.5 0 0126.5 27H23" stroke="#6F7568" stroke-width="1.6" stroke-linecap="round"/>
        <path d="M7.5 16H13.5" stroke="#B8B2A4" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M16 8V24" stroke="#F1EBDD" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="16" cy="16" r="3" fill="#8FE388"/>
        <path d="M18.5 16H21V11H24.5" stroke="#7FB7D8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div>
        <div class="title">Hydrogenuine</div>
        <div class="sub">GOVERNED RESEARCH SOAK</div>
      </div>
    </div>
    <nav>
      <div class="hg-eyebrow" style="padding:8px 10px 6px">Proof chain</div>
      {nav_html}
    </nav>
    <div class="sidebar-status">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--hg-green)"></span>
        <span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-muted)">run complete</span>
      </div>
      <div style="font-family:var(--font-mono);font-size:10px;color:var(--hg-faint)">{escape(session_id)}</div>
    </div>
  </aside>
  <div class="main">
    <div class="top-bar">
      <div>
        <h1>Governed Research Soak · Live Recorded</h1>
        <div class="meta">session {escape(session_id)} · {escape(model_name)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        {_badge(verdict, verdict_tone)}
        {_badge(f"data: {data_tier}", "evidence")}
      </div>
    </div>
    <div class="stages">
      {"".join(stages)}
    </div>
    <div class="ledger">
      <div class="hg-eyebrow" style="margin-bottom:6px">Evidence ledger · append-only</div>
      {ledger_html}
    </div>
  </div>
</div>
</body>
</html>"""
