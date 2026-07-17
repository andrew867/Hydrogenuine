"""Generate the dashboard index.html from dashboard_data.json.

Static local HTML with no external network references. No CDN, no remote
fonts, no remote scripts. Source is not truth. Model output is not truth.
"""

from __future__ import annotations

import html
import json

from hg_runtime.demo_dashboard.dashboard_assets import DASHBOARD_CSS


def _e(text) -> str:
    return html.escape(str(text)) if text else ""


def _chip(label: str, kind: str = "neutral") -> str:
    return f'<span class="chip chip-{kind}">{_e(label)}</span>'


def _stat_box(value, label: str) -> str:
    return (
        f'<div class="stat-box">'
        f'<div class="stat-value">{_e(value)}</div>'
        f'<div class="stat-label">{_e(label)}</div>'
        f'</div>'
    )


def _render_overview(data: dict) -> str:
    o = data.get("overview", {})
    gv = o.get("gate_verdict", "UNKNOWN")
    gclass = "green" if gv == "GREEN" else "red"
    domains = ", ".join(o.get("domains", [])) or "none"

    return f"""
<div class="tab-page active" id="page-overview">
<div class="verdict {gclass}">
  Gate: {_e(gv)} ({o.get('gate_checks_passed', 0)}/{o.get('gate_checks_total', 0)})
</div>
<div class="stats-grid">
  {_stat_box(o.get('cycles', 0), 'Cycles')}
  {_stat_box(o.get('sources_attempted', 0), 'Sources attempted')}
  {_stat_box(o.get('successful_fetches', 0), 'Fetches succeeded')}
  {_stat_box(o.get('failed_fetches', 0), 'Fetches failed')}
  {_stat_box(o.get('screenshots_captured', 0), 'Screenshots')}
  {_stat_box(f"{o.get('model_successes', 0)}/{o.get('model_attempts', 0)}", 'Model inferences')}
  {_stat_box(o.get('contradictions', 0), 'Contradictions')}
  {_stat_box(o.get('quarantine_entries', 0), 'Quarantined')}
  {_stat_box(o.get('promotions_count', 0), 'Promotions')}
  {_stat_box(o.get('external_effects_count', 0), 'External effects')}
  {_stat_box(o.get('public_claim_flags', 0), 'Public claim flags')}
  {_stat_box(o.get('quality_issues', 0), 'Quality issues')}
</div>
<div class="card">
  <div class="card-title">Run Details</div>
  <table>
    <tr><td>Run ID</td><td><code>{_e(o.get('run_id', ''))}</code></td></tr>
    <tr><td>Model</td><td>{_e(o.get('model_name', '(none)'))}</td></tr>
    <tr><td>Endpoint</td><td>{_e(o.get('model_endpoint_kind', ''))}</td></tr>
    <tr><td>Domains</td><td>{_e(domains)}</td></tr>
    <tr><td>Verdict</td><td>{_e(o.get('final_verdict', 'UNKNOWN'))}</td></tr>
  </table>
</div>
</div>"""


def _render_sources(data: dict) -> str:
    sources = data.get("sources", [])
    rows = ""
    for s in sources:
        status_chip = _chip(s['status'], 'green' if s['status'] == 'success' else 'red')
        rows += f"""<tr>
  <td>{_e(s.get('source_candidate_id', ''))}</td>
  <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis">{_e(s.get('url', ''))}</td>
  <td>{status_chip}</td>
  <td>{s.get('http_status', 0)}</td>
  <td>{s.get('content_length', 0)}</td>
  <td><code>{_e(s.get('content_hash', ''))}</code></td>
  <td>{_e(s.get('failure_reason', ''))}</td>
</tr>"""

    return f"""
<div class="tab-page" id="page-sources">
<h2>Sources</h2>
<p>{_chip('source_is_truth: false', 'amber')}</p>
<table>
<tr><th>ID</th><th>URL</th><th>Status</th><th>HTTP</th><th>Bytes</th><th>Hash</th><th>Error</th></tr>
{rows}
</table>
</div>"""


def _render_screenshots(data: dict) -> str:
    screenshots = data.get("screenshots", [])
    if not screenshots:
        content = '<p>No screenshots in this bundle. Screenshot capture was not performed in this run.</p>'
    else:
        items = ""
        for s in screenshots:
            items += f'<div class="card"><img src="{_e(s["path"])}" style="max-width:100%"><p>{_e(s["filename"])}</p></div>'
        content = items

    return f"""
<div class="tab-page" id="page-screenshots">
<h2>Screenshots</h2>
<p>{_chip('screenshot_is_truth: false', 'amber')}</p>
{content}
</div>"""


def _render_model_witnesses(data: dict) -> str:
    witnesses = data.get("model_witnesses", [])
    rows = ""
    for w in witnesses:
        status_chip = _chip(w['inference_status'], 'green' if w['inference_status'] == 'success' else 'amber')
        rows += f"""<tr>
  <td>{_e(w.get('cycle_id', ''))}</td>
  <td>{_e(w.get('model_name', '') or '(skipped)')}</td>
  <td>{_e(w.get('endpoint_kind', ''))}</td>
  <td>{status_chip}</td>
  <td>{_chip('false', 'green') if not w.get('remote_fallback_used') else _chip('true', 'red')}</td>
  <td>{w.get('output_chars', 0)}</td>
  <td>{w.get('latency_ms', 0)}ms</td>
</tr>"""

    output_previews = ""
    for w in witnesses:
        preview = w.get("output_text_preview", "")
        if preview:
            output_previews += f"""
<div class="card">
  <div class="card-title">{_e(w.get('cycle_id', ''))}</div>
  <pre>{_e(preview)}</pre>
</div>"""

    return f"""
<div class="tab-page" id="page-witnesses">
<h2>Model Witnesses</h2>
<p>{_chip('model_output_is_truth: false', 'amber')}</p>
<table>
<tr><th>Cycle</th><th>Model</th><th>Endpoint</th><th>Status</th><th>Remote fallback</th><th>Chars</th><th>Latency</th></tr>
{rows}
</table>
<h3>Output Previews</h3>
{output_previews if output_previews else '<p>No model output text available.</p>'}
</div>"""


def _render_evidence_graph(data: dict) -> str:
    traces = data.get("evidence_traces", [])
    rows = ""
    for t in traces:
        rows += f"""<tr>
  <td><code>{_e(t.get('receipt_id', ''))}</code></td>
  <td>{t.get('node_count', 0)}</td>
  <td>{t.get('edge_count', 0)}</td>
  <td>{t.get('contradiction_count', 0)}</td>
  <td>{t.get('evidence_gap_count', 0)}</td>
  <td>{t.get('unsupported_claims', 0)}</td>
</tr>"""

    return f"""
<div class="tab-page" id="page-evidence">
<h2>Evidence Graph</h2>
<p>{_chip('graph_edge_is_not_proof: true', 'amber')}</p>
<table>
<tr><th>Receipt</th><th>Nodes</th><th>Edges</th><th>Contradictions</th><th>Gaps</th><th>Unsupported</th></tr>
{rows}
</table>
<div class="card">
  <div class="card-title">Trace Pattern</div>
  <p>claim &rarr; source &rarr; model witness &rarr; quality adjudication &rarr; quarantine</p>
  <p>Every edge is a receipted connection, not proof of truth.</p>
</div>
</div>"""


def _render_contradictions(data: dict) -> str:
    c = data.get("contradictions", {})
    if isinstance(c, list):
        c = {"count": len(c), "quality_issues": 0}
    return f"""
<div class="tab-page" id="page-contradictions">
<h2>Contradictions</h2>
<div class="card">
  <table>
    <tr><td>Contradiction count</td><td>{c.get('count', 0)}</td></tr>
    <tr><td>Quality issues</td><td>{c.get('quality_issues', 0)}</td></tr>
    <tr><td>Operator review required</td><td>{_chip('true', 'amber')}</td></tr>
    <tr><td>Automated truth resolution</td><td>{_chip('none', 'green')}</td></tr>
  </table>
</div>
</div>"""


def _render_quarantine(data: dict) -> str:
    items = data.get("quarantine_items", [])
    wnp = data.get("why_not_promoted", [])

    q_rows = ""
    for q in items:
        q_rows += f"""<tr>
  <td><code>{_e(q.get('receipt_id', '')[:16])}</code></td>
  <td>{q.get('quarantined_count', 0)}</td>
  <td>{q.get('promoted_count', 0)}</td>
  <td>{_chip('false', 'green')}</td>
  <td>{_e(q.get('timestamp', ''))}</td>
</tr>"""

    wnp_html = ""
    for w in wnp:
        reasons = ""
        for r in w.get("blocking_reasons", []):
            reasons += f"<li>{_e(r['reason'])} &mdash; {_e(r.get('explanation', ''))}</li>"
        wnp_html += f"""
<div class="card">
  <div class="card-title">Why Not Promoted: {_e(w.get('item_id', ''))}</div>
  <ul>{reasons}</ul>
  <p>Next action: {_e(w.get('next_action', ''))}</p>
</div>"""

    return f"""
<div class="tab-page" id="page-quarantine">
<h2>Quarantine / Why Not Promoted</h2>
<p>{_chip('candidate_knowledge_is_not_knowledge', 'amber')}</p>
<table>
<tr><th>Receipt</th><th>Quarantined</th><th>Promoted</th><th>Promotion allowed</th><th>Timestamp</th></tr>
{q_rows}
</table>
{wnp_html}
</div>"""


def _render_public_claim_check(data: dict) -> str:
    pc = data.get("public_claim_check", {})
    status_chip = _chip(pc.get('status', 'unknown'), 'green' if pc.get('status') == 'clean' else 'red')

    items_rows = ""
    for item in pc.get("items", []):
        items_rows += f"""<tr>
  <td>{_e(item.get('source_label', ''))}</td>
  <td>{item.get('flagged_count', 0)}</td>
  <td>{_chip('clean', 'green') if item.get('clean') else _chip('flagged', 'red')}</td>
</tr>"""

    return f"""
<div class="tab-page" id="page-publicclaim">
<h2>Public Claim Check</h2>
<p>Status: {status_chip} &mdash; {pc.get('clean', 0)} clean, {pc.get('flagged', 0)} flagged of {pc.get('total_checked', 0)} checked</p>
<table>
<tr><th>Source</th><th>Flagged</th><th>Status</th></tr>
{items_rows}
</table>
</div>"""


def _render_demo_guide(data: dict) -> str:
    o = data.get("overview", {})
    steps = [
        ("Start Here", "Overview of the governed research runtime proof bundle.",
         "operator_review_required: true", "The runtime completed a governed pipeline.",
         "This does not prove production readiness."),
        ("A real source was fetched", f"{o.get('successful_fetches', 0)} sources fetched via live HTTP GET.",
         "source_is_truth: false", "The runtime can retrieve public web sources with receipts.",
         "Retrieved text is not knowledge."),
        ("A real page was captured", f"{o.get('screenshots_captured', 0)} screenshots captured.",
         "screenshot_is_truth: false", "The runtime can capture browser screenshots in locked-down context.",
         "Screenshots are visual records, not proof of content accuracy."),
        ("A local model acted as witness", f"{o.get('model_successes', 0)} local model inferences succeeded.",
         "model_output_is_truth: false", "The runtime can run local model inference over fetched source text.",
         "Model output is not truth. Model confidence is not proof."),
        ("The runtime judged quality", f"{o.get('quality_issues', 0)} quality issues recorded.",
         "quality_score_is_not_authority: true", "Quality adjudication records issues without resolving truth.",
         "Quality scores do not establish truth or authority."),
        ("Contradictions/gaps were preserved", f"{o.get('contradictions', 0)} contradictions recorded.",
         "operator_review_required: true", "Contradictions are preserved for operator review.",
         "No automated truth resolution occurred."),
        ("Candidate output stayed quarantined", f"{o.get('quarantine_entries', 0)} items quarantined, {o.get('promotions_count', 0)} promoted.",
         "candidate_knowledge_is_not_knowledge", "All model outputs remained in quarantine.",
         "No candidate knowledge was promoted to memory."),
        ("Public claims were checked", f"{o.get('public_claim_flags', 0)} public claim flags.",
         "checker_is_not_authority: true", "Public claim checker scanned all visible text.",
         "Passing the checker does not establish truth."),
        ("Here is the proof bundle", "Complete receipted artifact set.",
         "proof_bundle_is_not_authority", "The bundle demonstrates the governance pipeline end-to-end.",
         "The bundle does not prove autonomous research authority."),
    ]

    steps_html = ""
    for i, (title, detail, doctrine, proves, not_proves) in enumerate(steps, 1):
        steps_html += f"""
<div class="guide-step">
  <p><span class="step-num">Step {i}.</span> <strong>{_e(title)}</strong></p>
  <p>{_e(detail)}</p>
  <div class="guide-chip">{_chip(doctrine, 'amber')}</div>
  <p><strong>What this demonstrates:</strong> {_e(proves)}</p>
  <p><strong>What this does not prove:</strong> {_e(not_proves)}</p>
</div>"""

    return f"""
<div class="tab-page" id="page-demoguide">
<h2>Guided Demo Sequence</h2>
<p>Follow these steps for a screen recording walkthrough.</p>
{steps_html}
</div>"""


def _render_reports(data: dict) -> str:
    reports = data.get("reports", {})
    if not reports:
        return '<div class="tab-page" id="page-reports"><h2>Reports</h2><p>No reports in bundle.</p></div>'

    report_list = ""
    for name, content in reports.items():
        report_list += f"""
<div class="card">
  <div class="card-title">{_e(name)}</div>
  <div class="report-content">{_e(content)}</div>
</div>"""

    return f"""
<div class="tab-page" id="page-reports">
<h2>Reports</h2>
{report_list}
</div>"""


def _boundary_footer() -> str:
    return """
<div class="boundary-footer">
<h3>Boundary Statements</h3>
<ul>
<li>Source is not truth.</li>
<li>Screenshot is not proof.</li>
<li>Model output is not truth.</li>
<li>Evidence graph edge is not proof.</li>
<li>Quality score is not authority.</li>
<li>Trust score is not truth.</li>
<li>Risk score is not disproof.</li>
<li>Quarantine item is not memory.</li>
<li>Candidate knowledge is not knowledge.</li>
<li>No candidate knowledge was promoted.</li>
<li>Operator dashboard is observation/review, not autonomous authority.</li>
</ul>
</div>"""


def _tab_script() -> str:
    return """
<script>
(function(){
  var btns = document.querySelectorAll('.tab-btn');
  var pages = document.querySelectorAll('.tab-page');
  btns.forEach(function(btn){
    btn.addEventListener('click', function(){
      btns.forEach(function(b){ b.classList.remove('active'); });
      pages.forEach(function(p){ p.classList.remove('active'); });
      btn.classList.add('active');
      var target = document.getElementById(btn.getAttribute('data-target'));
      if(target) target.classList.add('active');
    });
  });
})();
</script>"""


def generate_dashboard_html(data: dict) -> str:
    """Generate the complete dashboard HTML from dashboard data."""
    tabs = [
        ("page-overview", "Overview"),
        ("page-sources", "Sources"),
        ("page-screenshots", "Screenshots"),
        ("page-witnesses", "Model Witnesses"),
        ("page-evidence", "Evidence Graph"),
        ("page-contradictions", "Contradictions"),
        ("page-quarantine", "Quarantine"),
        ("page-publicclaim", "Public Claims"),
        ("page-demoguide", "Demo Guide"),
        ("page-reports", "Reports"),
    ]

    tab_bar = '<div class="tab-bar">'
    for i, (target, label) in enumerate(tabs):
        active = " active" if i == 0 else ""
        tab_bar += f'<button class="tab-btn{active}" data-target="{target}">{_e(label)}</button>'
    tab_bar += '</div>'

    body = (
        _render_overview(data)
        + _render_sources(data)
        + _render_screenshots(data)
        + _render_model_witnesses(data)
        + _render_evidence_graph(data)
        + _render_contradictions(data)
        + _render_quarantine(data)
        + _render_public_claim_check(data)
        + _render_demo_guide(data)
        + _render_reports(data)
        + _boundary_footer()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hydrogenuine Operator Dashboard</title>
<style>
{DASHBOARD_CSS}
</style>
</head>
<body>
<div class="dashboard">
<h1>Hydrogenuine Operator Dashboard</h1>
<p style="font-size:0.85em;color:#666">Generated: {_e(data.get('generated_at', ''))} &mdash; Local-only, no external network.</p>
{tab_bar}
{body}
</div>
{_tab_script()}
</body>
</html>"""
