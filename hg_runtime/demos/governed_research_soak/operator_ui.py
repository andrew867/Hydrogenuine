"""Generate the operator review console HTML and run Playwright capture.

Uses V3 design tokens and console UI patterns. The HTML is self-contained
with embedded proof data and makes fetch() calls to the local server API
for approve/deny actions.
"""

from __future__ import annotations

import json
import time
from html import escape
from pathlib import Path


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


def generate_operator_ui(bundle_dir: str | Path, server_port: int) -> str:
    """Generate operator console HTML driven by real proof bundle data."""
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
    operator_id_rec = _read_json(bd / "operator_identity.json") or {}

    session_id = session.get("session_id", "unknown")
    question = session.get("question", "")
    model_name = provider.get("model_name", "unknown")
    endpoint = provider.get("endpoint_base_url", "unknown")
    first_call = provider.get("first_call", {})
    entries = quarantine.get("entries", [])
    nodes = evidence.get("nodes", [])
    edges = evidence.get("edges", [])

    # Build candidates JSON for the review queue
    candidates_json = json.dumps([
        {
            "id": e.get("candidate_id", f"candidate-{i}"),
            "text": e.get("content_summary", "")[:200],
            "state": e.get("state", "quarantined"),
            "source": e.get("source", ""),
            "model_id": e.get("model_id", ""),
            "quality_receipt_id": e.get("quality_receipt_id", ""),
            "source_receipt_id": e.get("source_receipt_id", ""),
        }
        for i, e in enumerate(entries)
    ])

    sources_json = json.dumps([
        {
            "url": s.get("url", ""),
            "title": s.get("title", ""),
            "content_hash": s.get("content_hash", "")[:24] + "...",
            "source_type": s.get("source_type", ""),
            "label": s.get("label", ""),
        }
        for s in sources
    ])

    evidence_json = json.dumps({
        "nodes": [{"id": n.get("node_id", ""), "type": n.get("node_type", ""), "label": n.get("label", "")[:60]} for n in nodes],
        "edges": [{"type": e.get("edge_type", ""), "from": e.get("from_node", ""), "to": e.get("to_node", "")} for e in edges],
    })

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hydrogenuine — Operator Review Console · Live</title>
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
}}
*,*::before,*::after {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0;background:var(--hg-bg);color:var(--hg-text);font-family:var(--font-body);font-size:14px;line-height:1.5; }}
.hg-eyebrow {{ font-family:var(--font-mono);font-size:11px;text-transform:uppercase;letter-spacing:0.16em;color:var(--hg-faint);font-weight:500; }}
.hg-hash {{ font-family:var(--font-mono);font-size:11px;color:var(--hg-blue);word-break:break-all; }}
::selection {{ background:rgba(45,79,54,0.6);color:var(--hg-text); }}
* {{ scrollbar-width:thin;scrollbar-color:var(--hg-border) transparent; }}

.console {{ display:flex;height:100vh; }}
.sidebar {{ width:240px;flex-shrink:0;background:var(--hg-panel);border-right:1px solid var(--hg-border);display:flex;flex-direction:column; }}
.sidebar-logo {{ padding:18px 16px;border-bottom:1px solid var(--hg-border);display:flex;align-items:center;gap:10px; }}
.sidebar-logo .title {{ font-family:var(--font-display);font-size:14px;font-weight:600; }}
.sidebar-logo .sub {{ font-family:var(--font-mono);font-size:10px;color:var(--hg-faint);letter-spacing:0.08em; }}
.sidebar nav {{ flex:1;overflow-y:auto;padding:8px 12px; }}
.nav-item {{ display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:var(--radius-sm);
  color:var(--hg-muted);font-family:var(--font-mono);font-size:12px;text-decoration:none;cursor:pointer;border:none;background:none;width:100%;text-align:left; }}
.nav-item:hover {{ background:var(--hg-card);color:var(--hg-text); }}
.nav-item.active {{ background:var(--hg-card);color:var(--hg-text);border:1px solid var(--hg-border); }}
.nav-num {{ color:var(--hg-faint);min-width:18px;font-size:11px; }}
.sidebar-status {{ padding:14px 16px;border-top:1px solid var(--hg-border); }}

.main {{ flex:1;display:flex;flex-direction:column;min-width:0; }}
.top-bar {{ display:flex;align-items:center;justify-content:space-between;padding:14px 24px;
  border-bottom:1px solid var(--hg-border);background:var(--hg-panel); }}
.top-bar h1 {{ font-family:var(--font-display);font-size:18px;font-weight:600;margin:0; }}
.stages {{ flex:1;overflow-y:auto;padding:24px; }}
.panel {{ background:var(--hg-card);border:1px solid var(--hg-border);border-radius:var(--radius-md);margin-bottom:16px;overflow:hidden; }}
.panel-header {{ display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px 20px;border-bottom:1px solid var(--hg-border-soft);background:var(--hg-panel); }}
.panel-header h3 {{ font-family:var(--font-display);font-size:16px;font-weight:600;margin:0; }}
.panel-body {{ padding:16px 20px; }}
.badge {{ display:inline-block;padding:2px 10px;border-radius:var(--radius-xs);font-family:var(--font-mono);font-size:11px;font-weight:600;letter-spacing:0.06em; }}
.badge-green {{ color:var(--hg-green);background:var(--hg-green-dim);border:1px solid var(--hg-green-line); }}
.badge-amber {{ color:var(--hg-amber);background:var(--hg-amber-dim);border:1px solid var(--hg-amber-line); }}
.badge-blue {{ color:var(--hg-blue);background:var(--hg-blue-dim);border:1px solid var(--hg-blue-line); }}
.badge-red {{ color:var(--hg-red);background:var(--hg-red-dim);border:1px solid var(--hg-red-line); }}
.badge-violet {{ color:var(--hg-violet);background:var(--hg-violet-dim);border:1px solid var(--hg-violet-line); }}
.meta-row {{ display:flex;justify-content:space-between;gap:16px;padding:6px 0;border-bottom:1px solid var(--hg-border-soft); }}
.meta-key {{ font-family:var(--font-mono);font-size:12px;color:var(--hg-faint); }}
.meta-val {{ font-family:var(--font-mono);font-size:12px;color:var(--hg-muted);text-align:right;word-break:break-all; }}

.btn {{ cursor:pointer;border:none;padding:10px 20px;border-radius:var(--radius-sm);font-family:var(--font-mono);font-size:12px;font-weight:600;letter-spacing:0.06em;transition:opacity 0.15s; }}
.btn:hover {{ opacity:0.85; }}
.btn:disabled {{ opacity:0.4;cursor:not-allowed; }}
.btn-approve {{ background:var(--hg-green);color:#070A08; }}
.btn-deny {{ background:var(--hg-red);color:#070A08; }}
.btn-hold {{ background:var(--hg-amber-dim);color:var(--hg-amber);border:1px solid var(--hg-amber-line); }}

.queue-item {{ padding:14px 16px;border-bottom:1px solid var(--hg-border);cursor:pointer;transition:background 0.12s; }}
.queue-item:hover {{ background:var(--hg-card-2); }}
.queue-item.selected {{ background:var(--hg-card);border-left:3px solid var(--hg-green); }}

.ledger-strip {{ border-top:1px solid var(--hg-border);background:var(--hg-panel);padding:10px 24px;max-height:120px;overflow-y:auto; }}

.disclaimer {{ position:fixed;left:0;right:0;top:0;z-index:999;font-family:var(--font-mono);font-size:11.5px;
  color:#cfe9c8;background:rgba(7,11,8,0.94);border-bottom:1px solid rgba(143,227,136,0.42);
  padding:7px 14px;text-align:center;letter-spacing:0.02em;backdrop-filter:blur(6px); }}
</style>
</head>
<body>
<div class="disclaimer" role="note" id="disclaimer-bar">Live operator review. Local signed operator. Not production auth. Candidate knowledge is not knowledge.</div>
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
        <div class="sub">OPERATOR CONSOLE</div>
      </div>
    </div>
    <nav>
      <div class="hg-eyebrow" style="padding:8px 12px 6px">Proof chain</div>
      <a href="#panel-run" class="nav-item"><span class="nav-num">01</span>Run</a>
      <a href="#panel-model" class="nav-item"><span class="nav-num">02</span>Model</a>
      <a href="#panel-quality" class="nav-item"><span class="nav-num">03</span>Quality</a>
      <a href="#panel-sources" class="nav-item"><span class="nav-num">04</span>Sources</a>
      <a href="#panel-evidence" class="nav-item"><span class="nav-num">05</span>Evidence</a>
      <a href="#panel-quarantine" class="nav-item"><span class="nav-num">06</span>Quarantine</a>
      <div class="hg-eyebrow" style="padding:14px 12px 6px">Operator</div>
      <a href="#panel-review" class="nav-item"><span class="nav-num">07</span>Review Queue</a>
      <a href="#panel-decisions" class="nav-item"><span class="nav-num">08</span>Decisions</a>
      <a href="#panel-promotion" class="nav-item"><span class="nav-num">09</span>Promotion</a>
      <a href="#panel-document" class="nav-item"><span class="nav-num">10</span>Document</a>
      <a href="#panel-bundle" class="nav-item"><span class="nav-num">11</span>Bundle</a>
    </nav>
    <div class="sidebar-status">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--hg-green);animation:pulse 2s infinite"></span>
        <span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-muted)">runtime live</span>
      </div>
      <div style="font-family:var(--font-mono);font-size:10px;color:var(--hg-faint)">{escape(session_id)}</div>
    </div>
  </aside>
  <div class="main">
    <div class="top-bar">
      <div>
        <h1>Operator Review Console</h1>
        <div style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint);margin-top:2px">session {escape(session_id)} · {escape(model_name)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <span id="verdict-badge" class="badge badge-amber">PENDING REVIEW</span>
        <span class="badge badge-blue">data: live</span>
      </div>
    </div>
    <div class="stages" id="stages-container">

      <!-- Panel 1: Run Header -->
      <div class="panel" id="panel-run">
        <div class="panel-header"><h3>Run Configuration</h3><span class="badge badge-blue">LIVE</span></div>
        <div class="panel-body">
          <div class="meta-row"><span class="meta-key">session_id</span><span class="meta-val" style="color:var(--hg-blue)">{escape(session_id)}</span></div>
          <div class="meta-row"><span class="meta-key">question</span><span class="meta-val">{escape(question[:100])}</span></div>
          <div class="meta-row"><span class="meta-key">model_endpoint</span><span class="meta-val" style="color:var(--hg-green)">{escape(endpoint)}</span></div>
          <div class="meta-row"><span class="meta-key">model</span><span class="meta-val" style="color:var(--hg-green)">{escape(model_name)}</span></div>
          <div class="meta-row"><span class="meta-key">run_mode</span><span class="meta-val" style="color:var(--hg-green)">LIVE LOCAL MODEL</span></div>
          <div class="meta-row"><span class="meta-key">source_mode</span><span class="meta-val" style="color:var(--hg-green)">LIVE ALLOWLIST</span></div>
          <div class="meta-row"><span class="meta-key">operator_mode</span><span class="meta-val" style="color:var(--hg-amber)">CLAUDE CODE LOCAL SIGNED OPERATOR</span></div>
          <div class="meta-row"><span class="meta-key">production_operator_auth</span><span class="meta-val" style="color:var(--hg-red)">false</span></div>
          <div class="meta-row"><span class="meta-key">operator_id</span><span class="meta-val" style="color:var(--hg-blue)">{escape(operator_id_rec.get("operator_id", ""))}</span></div>
          <div class="meta-row"><span class="meta-key">key_fingerprint</span><span class="meta-val" style="color:var(--hg-blue)">{escape(operator_id_rec.get("key_fingerprint", ""))}</span></div>
        </div>
      </div>

      <!-- Panel 2: Model Proposal -->
      <div class="panel" id="panel-model">
        <div class="panel-header"><h3>Model Proposal</h3><span class="badge badge-green">LIVE LOCAL MODEL</span></div>
        <div class="panel-body">
          <div class="meta-row"><span class="meta-key">provider_receipt</span><span class="meta-val" style="color:var(--hg-blue)">{escape(provider.get("provider_receipt_id", ""))}</span></div>
          <div class="meta-row"><span class="meta-key">endpoint</span><span class="meta-val" style="color:var(--hg-green)">{escape(endpoint)}</span></div>
          <div class="meta-row"><span class="meta-key">model</span><span class="meta-val" style="color:var(--hg-green)">{escape(model_name)}</span></div>
          <div class="meta-row"><span class="meta-key">local_provider</span><span class="meta-val" style="color:var(--hg-green)">true</span></div>
          <div class="meta-row"><span class="meta-key">cloud_provider</span><span class="meta-val" style="color:var(--hg-red)">false</span></div>
          <div class="meta-row"><span class="meta-key">response_hash</span><span class="meta-val hg-hash">{escape(first_call.get("response_hash", "")[:32])}</span></div>
          <div class="meta-row"><span class="meta-key">latency</span><span class="meta-val">{first_call.get("latency_s", "?")}s</span></div>
          <div style="margin-top:12px;padding:12px;background:var(--hg-bg);border:1px solid var(--hg-border);border-radius:var(--radius-sm);max-height:180px;overflow-y:auto">
            <div style="font-family:var(--font-mono);font-size:11px;color:var(--hg-muted);white-space:pre-wrap;line-height:1.5">{escape(proposal.get("content", "")[:600])}</div>
          </div>
        </div>
      </div>

      <!-- Panel 3: Quality Gate -->
      <div class="panel" id="panel-quality">
        <div class="panel-header"><h3>Quality Gate</h3><span class="badge badge-amber">{escape(quality.get("quality_class", "UNKNOWN"))}</span></div>
        <div class="panel-body">
          <div style="padding:12px;background:var(--hg-red-dim);border:1px solid var(--hg-red-line);border-radius:var(--radius-sm);margin-bottom:12px">
            <div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-red)">{escape(hold.get("reason", ""))}</div>
          </div>
          <div class="meta-row"><span class="meta-key">quality_class</span><span class="meta-val" style="color:var(--hg-amber)">{escape(quality.get("quality_class", ""))}</span></div>
          <div class="meta-row"><span class="meta-key">issues</span><span class="meta-val">{escape(", ".join(quality.get("issues", [])))}</span></div>
          <div class="meta-row"><span class="meta-key">route</span><span class="meta-val">{escape(quality.get("route", ""))}</span></div>
          <div class="meta-row"><span class="meta-key">action</span><span class="meta-val" style="color:var(--hg-red)">{escape(hold.get("action", ""))}</span></div>
          <div class="meta-row"><span class="meta-key">receipt_hash</span><span class="meta-val hg-hash">{escape(quality.get("hash", "")[:32])}</span></div>
        </div>
      </div>

      <!-- Panel 4: Source Capture -->
      <div class="panel" id="panel-sources">
        <div class="panel-header"><h3>Source Capture</h3><span class="badge badge-green">{len(sources)} LIVE SOURCES</span></div>
        <div class="panel-body" id="sources-container">
          {"".join(f'''<div style="padding:12px;background:var(--hg-bg);border:1px solid var(--hg-border);border-radius:var(--radius-sm);margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint)">source-{i+1}</span>
              <span class="badge badge-green">CAPTURED</span>
            </div>
            <div class="meta-row"><span class="meta-key">url</span><span class="meta-val" style="color:var(--hg-blue)">{escape(s.get("url",""))}</span></div>
            <div class="meta-row"><span class="meta-key">title</span><span class="meta-val">{escape(s.get("title","")[:50])}</span></div>
            <div class="meta-row"><span class="meta-key">type</span><span class="meta-val">{escape(s.get("source_type",""))}</span></div>
            <div class="meta-row"><span class="meta-key">label</span><span class="meta-val" style="color:var(--hg-amber)">{escape(s.get("label",""))}</span></div>
            <div class="meta-row"><span class="meta-key">content_hash</span><span class="meta-val hg-hash">{escape(s.get("content_hash","")[:24])}</span></div>
          </div>''' for i, s in enumerate(sources))}
        </div>
      </div>

      <!-- Panel 5: Evidence Graph -->
      <div class="panel" id="panel-evidence">
        <div class="panel-header"><h3>Evidence Graph</h3><span class="badge badge-blue">{len(nodes)} NODES · {len(edges)} EDGES</span></div>
        <div class="panel-body">
          {"".join(f'''<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--hg-border-soft)">
            <span class="badge {"badge-blue" if n.get("node_type")=="claim" else "badge-green" if n.get("node_type")=="source_candidate" else "badge-red"}">{escape(n.get("node_type",""))}</span>
            <span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-muted)">{escape(n.get("label","")[:60])}</span>
          </div>''' for n in nodes)}
        </div>
      </div>

      <!-- Panel 6: Memory Quarantine -->
      <div class="panel" id="panel-quarantine">
        <div class="panel-header"><h3>Memory Quarantine</h3><span class="badge badge-violet">QUARANTINED</span></div>
        <div class="panel-body">
          {"".join(f'''<div style="padding:10px;background:var(--hg-bg);border:1px solid var(--hg-border);border-radius:var(--radius-sm);margin-bottom:6px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint)">{escape(e.get("candidate_id",""))}</span>
              <span class="badge badge-violet">{escape(e.get("state","quarantined").upper())}</span>
            </div>
            <div style="font-family:var(--font-body);font-size:13px;color:var(--hg-muted);line-height:1.4">{escape(e.get("content_summary","")[:100])}</div>
          </div>''' for e in entries)}
          <div style="margin-top:10px">
            <div class="meta-row"><span class="meta-key">candidate_knowledge_is_not_knowledge</span><span class="meta-val" style="color:var(--hg-green)">{str(quarantine.get("candidate_knowledge_is_not_knowledge", True)).lower()}</span></div>
            <div class="meta-row"><span class="meta-key">promotion_requires_operator_review</span><span class="meta-val" style="color:var(--hg-green)">{str(quarantine.get("promotion_requires_operator_review", True)).lower()}</span></div>
            <div class="meta-row"><span class="meta-key">promotion_allowed</span><span class="meta-val" style="color:var(--hg-red)">{str(quarantine.get("promotion_allowed", False)).lower()}</span></div>
          </div>
        </div>
      </div>

      <!-- Panel 7: Operator Review Queue -->
      <div class="panel" id="panel-review">
        <div class="panel-header"><h3>Operator Review Queue</h3><span class="badge badge-amber" id="queue-badge">PENDING</span></div>
        <div class="panel-body" id="review-queue">
          <div id="queue-items"></div>
          <div id="review-detail" style="display:none;margin-top:16px;padding:16px;background:var(--hg-bg);border:1px solid var(--hg-border);border-radius:var(--radius-sm)">
            <div id="detail-content"></div>
            <div style="display:flex;gap:10px;margin-top:16px" id="action-buttons">
              <button class="btn btn-approve" id="btn-approve" onclick="handleApprove()">APPROVE</button>
              <button class="btn btn-deny" id="btn-deny" onclick="handleDeny()">DENY</button>
              <button class="btn btn-hold" id="btn-hold" onclick="handleHold()">HOLD</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel 8: Operator Decision Receipts -->
      <div class="panel" id="panel-decisions">
        <div class="panel-header"><h3>Operator Decisions</h3><span class="badge badge-amber" id="decisions-badge">AWAITING</span></div>
        <div class="panel-body" id="decisions-container">
          <div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-faint);padding:20px;text-align:center">
            Decisions will appear here after operator review.
          </div>
        </div>
      </div>

      <!-- Panel 9: Promotion -->
      <div class="panel" id="panel-promotion">
        <div class="panel-header"><h3>Promotion</h3><span class="badge badge-amber" id="promotion-badge">AWAITING DECISIONS</span></div>
        <div class="panel-body" id="promotion-container">
          <div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-faint);padding:20px;text-align:center">
            Promotion status will appear after operator decisions.
          </div>
        </div>
      </div>

      <!-- Panel 10: Final Document -->
      <div class="panel" id="panel-document">
        <div class="panel-header"><h3>Final Document</h3><span class="badge badge-amber" id="document-badge">AWAITING</span></div>
        <div class="panel-body" id="document-container">
          <div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-faint);padding:20px;text-align:center">
            Final document will be generated after promotion.
          </div>
        </div>
      </div>

      <!-- Panel 11: Proof Bundle -->
      <div class="panel" id="panel-bundle">
        <div class="panel-header"><h3>Proof Bundle</h3><span class="badge badge-blue" id="bundle-badge">ASSEMBLING</span></div>
        <div class="panel-body" id="bundle-container">
          <div style="font-family:var(--font-mono);font-size:12px;color:var(--hg-faint);padding:20px;text-align:center">
            Bundle summary will appear after all phases complete.
          </div>
        </div>
      </div>

    </div>
    <div class="ledger-strip" id="ledger">
      <div class="hg-eyebrow" style="margin-bottom:6px">Evidence ledger · append-only</div>
      <div id="ledger-entries"></div>
    </div>
  </div>
</div>

<style>@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}</style>

<script>
const API = "http://127.0.0.1:{server_port}";
const candidates = {candidates_json};
const sources = {sources_json};
const evidence = {evidence_json};
let selectedIdx = 0;
let decisionsMade = {{}};
let allDecisions = [];

function addLedger(event, status) {{
  const el = document.getElementById("ledger-entries");
  const colors = {{ allowed:"var(--hg-green)", refused:"var(--hg-red)", pending:"var(--hg-amber)", evidence:"var(--hg-blue)" }};
  const now = new Date().toTimeString().slice(0,8);
  el.innerHTML += '<div style="display:flex;align-items:center;gap:10px;padding:3px 0;font-family:var(--font-mono);font-size:11px">'
    + '<span style="width:8px;height:8px;border-radius:50%;background:' + (colors[status]||colors.pending) + ';flex-shrink:0"></span>'
    + '<span style="color:var(--hg-faint);min-width:60px">' + now + '</span>'
    + '<span style="color:var(--hg-muted)">' + event + '</span></div>';
  el.parentElement.scrollTop = el.parentElement.scrollHeight;
}}

function renderQueue() {{
  const el = document.getElementById("queue-items");
  el.innerHTML = "";
  candidates.forEach((c, i) => {{
    const state = decisionsMade[c.id] || "pending";
    const badgeClass = state === "approve" ? "badge-green" : state === "deny" ? "badge-red" : "badge-amber";
    const label = state === "approve" ? "APPROVED" : state === "deny" ? "DENIED" : "PENDING";
    const selected = i === selectedIdx ? " selected" : "";
    el.innerHTML += '<div class="queue-item' + selected + '" onclick="selectCandidate(' + i + ')">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
      + '<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint)">' + c.id + '</span>'
      + '<span class="badge ' + badgeClass + '">' + label + '</span></div>'
      + '<div style="font-family:var(--font-body);font-size:13px;color:var(--hg-text);line-height:1.4">' + c.text.slice(0,100) + '</div>'
      + '</div>';
  }});
  renderDetail();
  updateQueueBadge();
}}

function selectCandidate(i) {{
  selectedIdx = i;
  renderQueue();
}}

function renderDetail() {{
  const c = candidates[selectedIdx];
  if (!c) return;
  const detail = document.getElementById("review-detail");
  const content = document.getElementById("detail-content");
  detail.style.display = "block";
  const resolved = decisionsMade[c.id];
  content.innerHTML = '<div class="hg-eyebrow" style="margin-bottom:8px">Candidate detail</div>'
    + '<div class="meta-row"><span class="meta-key">candidate_id</span><span class="meta-val" style="color:var(--hg-blue)">' + c.id + '</span></div>'
    + '<div class="meta-row"><span class="meta-key">state</span><span class="meta-val">' + (resolved || c.state) + '</span></div>'
    + '<div class="meta-row"><span class="meta-key">source</span><span class="meta-val">' + c.source + '</span></div>'
    + '<div class="meta-row"><span class="meta-key">quality_receipt</span><span class="meta-val hg-hash">' + (c.quality_receipt_id||"").slice(0,24) + '</span></div>'
    + '<div style="margin-top:10px;padding:10px;background:var(--hg-bg);border:1px solid var(--hg-border);border-radius:var(--radius-sm)">'
    + '<div style="font-family:var(--font-body);font-size:13px;color:var(--hg-muted);line-height:1.5">' + c.text + '</div></div>';
  const btns = document.getElementById("action-buttons");
  btns.style.display = resolved ? "none" : "flex";
}}

function updateQueueBadge() {{
  const pending = candidates.filter(c => !decisionsMade[c.id]).length;
  const badge = document.getElementById("queue-badge");
  if (pending === 0) {{
    badge.className = "badge badge-green";
    badge.textContent = "ALL REVIEWED";
  }} else {{
    badge.className = "badge badge-amber";
    badge.textContent = pending + " PENDING";
  }}
}}

async function handleApprove() {{
  const c = candidates[selectedIdx];
  if (!c || decisionsMade[c.id]) return;
  const resp = await fetch(API + "/api/decide", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{
      action: "approve",
      candidate_id: c.id,
      reason: "Source-supported finding approved for provisional use by local signed operator",
      receipt_ids_reviewed: [c.quality_receipt_id, c.source_receipt_id].filter(Boolean),
    }}),
  }});
  const decision = await resp.json();
  decisionsMade[c.id] = "approve";
  allDecisions.push(decision);
  renderQueue();
  renderDecisions();
  addLedger("operator approved " + c.id, "allowed");
}}

async function handleDeny() {{
  const c = candidates[selectedIdx];
  if (!c || decisionsMade[c.id]) return;
  const resp = await fetch(API + "/api/decide", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{
      action: "deny",
      candidate_id: c.id,
      reason: "Insufficient source support or overclaim risk — denied by local signed operator",
      receipt_ids_reviewed: [c.quality_receipt_id, c.source_receipt_id].filter(Boolean),
    }}),
  }});
  const decision = await resp.json();
  decisionsMade[c.id] = "deny";
  allDecisions.push(decision);
  renderQueue();
  renderDecisions();
  addLedger("operator denied " + c.id, "refused");
}}

async function handleHold() {{
  const c = candidates[selectedIdx];
  if (!c || decisionsMade[c.id]) return;
  decisionsMade[c.id] = "hold";
  renderQueue();
  addLedger("operator held " + c.id, "pending");
}}

function renderDecisions() {{
  const el = document.getElementById("decisions-container");
  if (allDecisions.length === 0) return;
  const badge = document.getElementById("decisions-badge");
  badge.className = "badge badge-green";
  badge.textContent = allDecisions.length + " SIGNED";
  el.innerHTML = "";
  allDecisions.forEach(d => {{
    const tone = d.decision_action === "approve" ? "badge-green" : "badge-red";
    el.innerHTML += '<div style="padding:12px;background:var(--hg-bg);border:1px solid var(--hg-border);border-radius:var(--radius-sm);margin-bottom:8px">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
      + '<span style="font-family:var(--font-mono);font-size:11px;color:var(--hg-faint)">' + d.target_candidate_id + '</span>'
      + '<span class="badge ' + tone + '">' + d.decision_action.toUpperCase() + '</span></div>'
      + '<div class="meta-row"><span class="meta-key">operator_id</span><span class="meta-val" style="color:var(--hg-blue)">' + d.operator_id + '</span></div>'
      + '<div class="meta-row"><span class="meta-key">decision_source</span><span class="meta-val" style="color:var(--hg-green)">' + d.decision_source + '</span></div>'
      + '<div class="meta-row"><span class="meta-key">operator_mode</span><span class="meta-val">' + d.operator_mode + '</span></div>'
      + '<div class="meta-row"><span class="meta-key">timestamp</span><span class="meta-val">' + d.decision_timestamp + '</span></div>'
      + '<div class="meta-row"><span class="meta-key">payload_hash</span><span class="meta-val hg-hash">' + (d.payload_hash||"").slice(0,32) + '</span></div>'
      + '<div class="meta-row"><span class="meta-key">signature</span><span class="meta-val hg-hash">' + (d.signature||"").slice(0,32) + '...</span></div>'
      + '<div class="meta-row"><span class="meta-key">production_operator_auth</span><span class="meta-val" style="color:var(--hg-red)">false</span></div>'
      + '<div class="meta-row"><span class="meta-key">reason</span><span class="meta-val">' + (d.decision_reason||"").slice(0,80) + '</span></div>'
      + '</div>';
  }});
}}

// Initialize
addLedger("session started", "evidence");
addLedger("model probed — live local endpoint", "allowed");
addLedger("first proposal generated", "evidence");
addLedger("quality gate held — needs source support", "refused");
addLedger("sources captured — {len(sources)} URLs", "allowed");
addLedger("evidence graph built", "evidence");
addLedger("{len(entries)} candidates quarantined", "pending");
addLedger("operator review queue ready", "pending");
renderQueue();
</script>
</body>
</html>"""


SCREENSHOT_STAGES = {
    1: "01_console_overview",
    2: "02_run_configuration",
    3: "03_model_proposal",
    4: "04_quality_gate",
    5: "05_source_capture",
    6: "06_evidence_graph",
    7: "07_memory_quarantine",
    8: "08_review_queue_pending",
    9: "09_approve_click",
    10: "10_deny_click",
    11: "11_decisions_signed",
    12: "12_ledger_trail",
    13: "13_final_state",
}


def capture_operator_ui(
    *,
    server_url: str,
    output_dir: str | Path,
    video: bool = True,
) -> dict:
    """Open operator console in Playwright, click approve/deny, record video + screenshots."""
    from playwright.sync_api import sync_playwright

    out = Path(output_dir)
    ss_dir = out / "screenshots"
    ss_dir.mkdir(exist_ok=True)
    rec_dir = out / "recording" if video else None
    if rec_dir:
        rec_dir.mkdir(exist_ok=True)

    result = {
        "screenshots": [],
        "video_path": None,
        "video_ok": False,
        "screenshot_ok": False,
        "approve_clicked": False,
        "deny_clicked": False,
        "decisions_count": 0,
        "errors": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx_args = {"viewport": {"width": 1440, "height": 900}}
        if rec_dir:
            ctx_args["record_video_dir"] = str(rec_dir)
            ctx_args["record_video_size"] = {"width": 1440, "height": 900}
        context = browser.new_context(**ctx_args)
        page = context.new_page()

        try:
            page.goto(server_url, wait_until="networkidle", timeout=15000)
            time.sleep(0.8)

            def _ss(stage: int) -> str:
                name = SCREENSHOT_STAGES[stage]
                path = str(ss_dir / f"{name}.png")
                page.screenshot(path=path, full_page=False)
                result["screenshots"].append(path)
                return path

            # 1: Full console overview
            _ss(1)

            # 2: Run configuration
            page.click('a[href="#panel-run"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-run").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(2)

            # 3: Model proposal
            page.click('a[href="#panel-model"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-model").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(3)

            # 4: Quality gate
            page.click('a[href="#panel-quality"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-quality").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(4)

            # 5: Source capture
            page.click('a[href="#panel-sources"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-sources").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(5)

            # 6: Evidence graph
            page.click('a[href="#panel-evidence"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-evidence").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(6)

            # 7: Memory quarantine
            page.click('a[href="#panel-quarantine"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-quarantine").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(7)

            # 8: Review queue (pending state)
            page.click('a[href="#panel-review"]')
            time.sleep(0.3)
            page.evaluate('document.getElementById("panel-review").scrollIntoView({behavior:"instant"})')
            time.sleep(0.5)
            _ss(8)

            # 9: Click APPROVE on the first candidate
            approve_btn = page.query_selector("#btn-approve")
            if approve_btn:
                approve_btn.click()
                time.sleep(1.0)
                result["approve_clicked"] = True
                _ss(9)

            # Select next candidate, click DENY
            candidates = page.query_selector_all(".queue-item")
            if len(candidates) > 1:
                candidates[1].click()
                time.sleep(0.5)
                deny_btn = page.query_selector("#btn-deny")
                if deny_btn:
                    deny_btn.click()
                    time.sleep(1.0)
                    result["deny_clicked"] = True
            _ss(10)

            # 11: Decisions panel
            page.click('a[href="#panel-decisions"]')
            time.sleep(0.5)
            page.evaluate('document.getElementById("panel-decisions").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(11)

            # Count decisions made via page JS
            decisions_count = page.evaluate("allDecisions.length")
            result["decisions_count"] = decisions_count

            # 12: Ledger trail — evidence graph shows the proof chain
            page.click('a[href="#panel-evidence"]')
            time.sleep(0.5)
            page.evaluate('document.getElementById("panel-evidence").scrollIntoView({behavior:"instant"})')
            time.sleep(0.3)
            _ss(12)

            # 13: Final state — back to top for overview
            page.click('a[href="#panel-run"]')
            time.sleep(0.3)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)
            _ss(13)

        except Exception as exc:
            result["errors"].append(str(exc))

        page.close()
        context.close()

        if rec_dir:
            videos = list(rec_dir.glob("*.webm"))
            if videos:
                target = rec_dir / "operator_ui_live.webm"
                if videos[0] != target:
                    videos[0].rename(target)
                result["video_path"] = str(target)
                result["video_ok"] = True

        browser.close()

    result["screenshot_ok"] = len(result["screenshots"]) >= 10
    return result
