"""HTML proof viewer generator for GRS demo bundle."""

from __future__ import annotations

import json
from pathlib import Path


CAPTURE_STATES = [
    ("session-start", "01_session_start.png"),
    ("model-proposal", "02_model_proposal.png"),
    ("quality-gate", "03_quality_gate_hold.png"),
    ("source-capture", "04_source_capture.png"),
    ("evidence-graph", "05_evidence_graph.png"),
    ("memory-quarantine", "06_memory_quarantine.png"),
    ("operator-review", "07_operator_review.png"),
    ("operator-decision", "08_operator_approval.png"),
    ("promotion-receipt", "09_promotion_receipt.png"),
    ("proof-summary", "10_proof_bundle_summary.png"),
]


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _json_block(data: dict | list | None) -> str:
    if data is None:
        return "<pre>Not available</pre>"
    return f"<pre>{_esc(json.dumps(data, indent=2, ensure_ascii=False))}</pre>"


def generate_report(bundle_dir: Path) -> str:
    d = bundle_dir

    config = _load_json(d / "demo_config.json") or {}
    session = _load_json(d / "session_receipt.json") or {}
    proposal = _load_json(d / "model_proposal_receipt.json") or {}
    quality = _load_json(d / "quality_gate_receipt.json") or {}
    hold = _load_json(d / "refusal_or_hold_receipt.json") or {}
    sources = _load_jsonl(d / "source_capture_receipts.jsonl")
    evidence = _load_json(d / "evidence_graph.json") or {}
    quarantine = _load_json(d / "memory_quarantine.json") or {}
    review = _load_json(d / "operator_review_packet.json") or {}
    decision = _load_json(d / "operator_decision_receipt.json") or {}
    promotion = _load_json(d / "promotion_receipt.json") or {}
    manifest = _load_json(d / "manifest.json") or {}
    final_answer = _load_text(d / "final_answer.md")
    claim_report = _load_text(d / "claim_boundary_report.md")

    verdict = manifest.get("verdict", "UNKNOWN")
    verdict_color = "#d4a017" if "YELLOW" in verdict else (
        "#2d8a4e" if "GREEN" in verdict else "#c0392b"
    )

    sections = []

    # Session start
    sections.append(f"""
    <section id="session-start">
      <h2>1. Session Start</h2>
      <div class="card">
        <div class="label">Session ID</div>
        <div class="value">{_esc(session.get('session_id', ''))}</div>
        <div class="label">Question</div>
        <div class="value">{_esc(session.get('question', ''))}</div>
        <div class="label">Data Tier</div>
        <div class="value">{_esc(session.get('data_tier', ''))}</div>
        <div class="label">Demo Mode</div>
        <div class="value">{session.get('demo_mode', '')}</div>
        <div class="label">Hash</div>
        <div class="hash">{_esc(session.get('hash', ''))}</div>
      </div>
    </section>
    """)

    # Model proposal
    content_preview = _esc(proposal.get("content", "")[:500])
    sections.append(f"""
    <section id="model-proposal">
      <h2>2. Model Proposal</h2>
      <div class="card">
        <div class="label">Model</div>
        <div class="value">{_esc(proposal.get('model_id', ''))}</div>
        <div class="label">Pass</div>
        <div class="value">{proposal.get('pass_number', '')}</div>
        <div class="label">Content (preview)</div>
        <div class="content">{content_preview}</div>
        <div class="label">Hash</div>
        <div class="hash">{_esc(proposal.get('hash', ''))}</div>
      </div>
    </section>
    """)

    # Quality gate
    sections.append(f"""
    <section id="quality-gate">
      <h2>3. Quality Gate</h2>
      <div class="card">
        <span class="badge badge-yellow">{_esc(quality.get('quality_class', ''))}</span>
        <div class="label">Issues</div>
        <div class="value">{_esc(', '.join(quality.get('issues', [])))}</div>
        <div class="label">Route</div>
        <div class="value">{_esc(quality.get('route', ''))}</div>
        <div class="label">Scores</div>
        {_json_block(quality.get('scores'))}
        <div class="label">Hash</div>
        <div class="hash">{_esc(quality.get('hash', ''))}</div>
      </div>
      <div class="card hold">
        <div class="label">HELD</div>
        <div class="value">{_esc(hold.get('reason', ''))}</div>
      </div>
    </section>
    """)

    # Source capture
    source_cards = ""
    for i, s in enumerate(sources, 1):
        source_cards += f"""
        <div class="card">
          <div class="label">Source {i}</div>
          <div class="value"><a href="{_esc(s.get('url', ''))}">{_esc(s.get('title', ''))}</a></div>
          <div class="label">Label</div>
          <span class="badge badge-green">{_esc(s.get('label', ''))}</span>
          <div class="label">Content Hash</div>
          <div class="hash">{_esc(s.get('content_hash', ''))}</div>
        </div>
        """
    sections.append(f"""
    <section id="source-capture">
      <h2>4. Source Capture</h2>
      {source_cards}
    </section>
    """)

    # Evidence graph
    node_count = len(evidence.get("nodes", []))
    edge_count = len(evidence.get("edges", []))
    eg_invariants = {
        k: v for k, v in evidence.items()
        if k not in ("schema", "session_id", "data_tier", "nodes", "edges")
    }
    sections.append(f"""
    <section id="evidence-graph">
      <h2>5. Evidence Graph</h2>
      <div class="card">
        <div class="label">Nodes</div>
        <div class="value">{node_count}</div>
        <div class="label">Edges</div>
        <div class="value">{edge_count}</div>
        <div class="label">Invariants</div>
        {_json_block(eg_invariants)}
      </div>
    </section>
    """)

    # Memory quarantine
    entries = quarantine.get("entries", [])
    q_invariants = {
        k: v for k, v in quarantine.items()
        if k not in ("schema", "entries")
    }
    entry_cards = ""
    for e in entries:
        state = e.get("state", "unknown")
        badge_class = "badge-green" if state == "promoted" else (
            "badge-yellow" if state in ("deferred", "approved_for_memory_by_gate") else "badge-red"
        )
        entry_cards += f"""
        <div class="card">
          <div class="label">{_esc(e.get('candidate_id', ''))}</div>
          <span class="badge {badge_class}">{_esc(state)}</span>
          <div class="value">{_esc(e.get('content_summary', '')[:120])}</div>
          <div class="label">promoted</div>
          <div class="value">{e.get('promotion_allowed', False)}</div>
        </div>
        """
    sections.append(f"""
    <section id="memory-quarantine">
      <h2>6. Memory Quarantine</h2>
      {entry_cards}
      <div class="card">
        <div class="label">Quarantine Invariants</div>
        {_json_block(q_invariants)}
      </div>
    </section>
    """)

    # Operator review
    sections.append(f"""
    <section id="operator-review">
      <h2>7. Operator Review Packet</h2>
      <div class="card">
        <div class="label">Operator Mode</div>
        <span class="badge badge-yellow">{_esc(review.get('operator_mode', ''))}</span>
        <div class="label">Candidates</div>
        <div class="value">{len(review.get('candidates_pending', []))}</div>
        <div class="label">Sources</div>
        <div class="value">{len(review.get('sources_used', []))}</div>
        <div class="label">Hash</div>
        <div class="hash">{_esc(review.get('hash', ''))}</div>
      </div>
    </section>
    """)

    # Operator decision
    dec_cards = ""
    for dd in decision.get("decisions", []):
        status = dd.get("status", "")
        badge_class = "badge-green" if "APPROVE" in status else "badge-yellow"
        dec_cards += f"""
        <div class="card">
          <div class="label">{_esc(dd.get('candidate_ref', ''))}</div>
          <span class="badge {badge_class}">{_esc(status)}</span>
          <div class="value">{_esc(dd.get('reason', ''))}</div>
        </div>
        """
    sections.append(f"""
    <section id="operator-decision">
      <h2>8. Operator Decision</h2>
      <div class="card">
        <div class="label">Operator</div>
        <div class="value">{_esc(decision.get('operator_identity', ''))}</div>
        <div class="label">Authenticated</div>
        <div class="value">{decision.get('authenticated', '')}</div>
      </div>
      {dec_cards}
      <div class="card">
        <div class="label">Neutral Flags</div>
        {_json_block(decision.get('neutral_flags'))}
      </div>
    </section>
    """)

    # Promotion receipt
    sections.append(f"""
    <section id="promotion-receipt">
      <h2>9. Promotion Receipt</h2>
      <div class="card">
        <div class="label">Promoted</div>
        <div class="value">{_esc(promotion.get('candidate_ref', 'none'))}</div>
        <div class="label">Chain</div>
        <div class="value">{_esc(' -> '.join(promotion.get('promotion_chain', [])))}</div>
        <div class="label">Provisional</div>
        <div class="value">{promotion.get('provisional', '')}</div>
        <div class="label">Hash</div>
        <div class="hash">{_esc(promotion.get('hash', ''))}</div>
      </div>
    </section>
    """)

    # Proof summary
    file_list = "<br>".join(_esc(f) for f in manifest.get("files", []))
    sections.append(f"""
    <section id="proof-summary">
      <h2>10. Proof Bundle Summary</h2>
      <div class="card">
        <div class="verdict" style="color: {verdict_color}">{_esc(verdict)}</div>
        <div class="label">Bundle ID</div>
        <div class="value">{_esc(manifest.get('bundle_id', ''))}</div>
        <div class="label">Files</div>
        <div class="value">{file_list}</div>
        <div class="label">Data Tier</div>
        <div class="value">{_esc(manifest.get('data_tier', ''))}</div>
        <div class="label">Manifest Hash</div>
        <div class="hash">{_esc(manifest.get('hash', ''))}</div>
      </div>
    </section>
    """)

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Governed Research Soak — Proof Report</title>
<style>
  :root {{
    --bg: #0e1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --green: #2d8a4e;
    --yellow: #d4a017;
    --red: #c0392b;
    --mono: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
  }}
  h1 {{
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
    color: var(--text);
  }}
  h2 {{
    font-size: 1.1rem;
    margin: 2rem 0 0.75rem;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
  }}
  .subtitle {{
    color: var(--text-muted);
    margin-bottom: 2rem;
    font-size: 0.85rem;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 0.75rem;
  }}
  .card.hold {{
    border-color: var(--yellow);
  }}
  .label {{
    color: var(--text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.5rem;
  }}
  .label:first-child {{ margin-top: 0; }}
  .value {{
    color: var(--text);
    margin-bottom: 0.25rem;
  }}
  .hash {{
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--text-muted);
    word-break: break-all;
  }}
  .content {{
    font-family: var(--mono);
    font-size: 0.8rem;
    white-space: pre-wrap;
    color: var(--text);
    margin: 0.5rem 0;
  }}
  .verdict {{
    font-size: 1.2rem;
    font-weight: 700;
    font-family: var(--mono);
    margin-bottom: 0.5rem;
  }}
  .badge {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-family: var(--mono);
    font-weight: 600;
  }}
  .badge-green {{ background: var(--green); color: #fff; }}
  .badge-yellow {{ background: var(--yellow); color: #000; }}
  .badge-red {{ background: var(--red); color: #fff; }}
  pre {{
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem;
    font-family: var(--mono);
    font-size: 0.75rem;
    overflow-x: auto;
    margin: 0.5rem 0;
    color: var(--text);
  }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  footer {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 0.75rem;
    text-align: center;
  }}
</style>
</head>
<body>
  <h1>Governed Research Soak</h1>
  <div class="subtitle">
    Hydrogenuine — Artificial Governed Intelligence Runtime<br>
    Demo proof report &middot; {_esc(manifest.get('generated_at', ''))}
  </div>

  {body}

  <footer>
    This is a demo artifact. Screenshot is not proof.<br>
    Receipt is not trust. Source is not truth.<br>
    Candidate knowledge is not knowledge.
  </footer>
</body>
</html>
"""


def capture_screenshots(html_path: str, output_dir: str) -> list[str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    captured = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"file://{html_path}")

        import os
        for section_id, filename in CAPTURE_STATES:
            element = page.query_selector(f"#{section_id}")
            if element:
                element.screenshot(path=os.path.join(output_dir, filename))
                captured.append(filename)

        browser.close()
    return captured
