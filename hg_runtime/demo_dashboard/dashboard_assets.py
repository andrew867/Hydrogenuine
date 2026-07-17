"""CSS assets for the demo dashboard. All local, no CDN, no remote fonts."""

from __future__ import annotations

DASHBOARD_CSS = """\
:root {
  --bg: #faf8f5;
  --fg: #1a1a1a;
  --border: #d4cfc7;
  --accent: #2a7d5f;
  --accent-bg: #eaf5f0;
  --warn: #c47a00;
  --warn-bg: #fff8e1;
  --fail: #c33;
  --fail-bg: #ffeaea;
  --chip-bg: #e8e4de;
  --mono: 'Courier New', 'Consolas', monospace;
  --sans: system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
  --card-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
}
.dashboard { max-width: 1100px; margin: 0 auto; padding: 1.5em 1em; }
h1 { font-size: 1.6em; border-bottom: 2px solid var(--fg); padding-bottom: 0.3em; margin-bottom: 0.5em; }
h2 { font-size: 1.2em; margin: 1.5em 0 0.5em; }
h3 { font-size: 1em; margin: 1em 0 0.3em; }

/* Nav tabs */
.tab-bar { display: flex; flex-wrap: wrap; gap: 0; border-bottom: 2px solid var(--border); margin-bottom: 1.5em; }
.tab-btn {
  background: none; border: none; padding: 0.6em 1.2em; cursor: pointer;
  font-size: 0.85em; font-family: var(--sans); color: var(--fg);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.tab-btn:hover { background: var(--chip-bg); }
.tab-btn.active { border-bottom-color: var(--accent); font-weight: 600; }
.tab-page { display: none; }
.tab-page.active { display: block; }

/* Cards */
.card {
  background: #fff; border: 1px solid var(--border); border-radius: 6px;
  padding: 1em; margin-bottom: 1em; box-shadow: var(--card-shadow);
}
.card-title { font-weight: 600; margin-bottom: 0.5em; font-size: 0.95em; }

/* Tables */
table { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 0.85em; }
th, td { border: 1px solid var(--border); padding: 0.4em 0.6em; text-align: left; }
th { background: var(--chip-bg); font-weight: 600; }

/* Chips */
.chip {
  display: inline-block; padding: 0.15em 0.6em; border-radius: 3px;
  font-size: 0.8em; font-family: var(--mono); font-weight: 600;
}
.chip-green { background: var(--accent-bg); color: var(--accent); }
.chip-red { background: var(--fail-bg); color: var(--fail); }
.chip-amber { background: var(--warn-bg); color: var(--warn); }
.chip-neutral { background: var(--chip-bg); color: var(--fg); }

/* Verdict */
.verdict { font-size: 1.8em; font-weight: 700; margin: 0.3em 0; }
.verdict.green { color: var(--accent); }
.verdict.red { color: var(--fail); }

/* Boundary footer */
.boundary-footer {
  background: var(--warn-bg); border-left: 4px solid var(--warn);
  padding: 0.8em 1em; margin: 2em 0 1em; font-size: 0.85em;
}
.boundary-footer ul { list-style: none; padding: 0; }
.boundary-footer li::before { content: '\\2022 '; color: var(--warn); font-weight: bold; }

/* Pre/code */
pre { background: #f4f2ee; border: 1px solid var(--border); padding: 0.8em; overflow-x: auto; font-size: 0.82em; font-family: var(--mono); border-radius: 4px; }
code { font-family: var(--mono); font-size: 0.9em; }

/* Stats grid */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.8em; margin: 1em 0; }
.stat-box {
  background: #fff; border: 1px solid var(--border); border-radius: 6px;
  padding: 0.8em; text-align: center; box-shadow: var(--card-shadow);
}
.stat-value { font-size: 1.6em; font-weight: 700; font-family: var(--mono); }
.stat-label { font-size: 0.75em; color: #666; margin-top: 0.2em; }

/* Demo guide */
.guide-step {
  border-left: 3px solid var(--accent); padding: 0.8em 1em; margin: 0.8em 0;
  background: #fff; border-radius: 0 6px 6px 0;
}
.guide-step .step-num { font-weight: 700; color: var(--accent); }
.guide-chip { margin-top: 0.4em; }

/* Report content */
.report-content { white-space: pre-wrap; font-size: 0.88em; max-height: 500px; overflow-y: auto; line-height: 1.6; }

/* Recording-friendly enhancements */
.dashboard { max-width: 1200px; }
body { font-size: 15px; line-height: 1.6; }
h1 { font-size: 1.8em; letter-spacing: -0.01em; }
h2 { font-size: 1.35em; }
.tab-btn { font-size: 0.92em; padding: 0.7em 1.4em; }
.stat-value { font-size: 1.8em; }
.stat-label { font-size: 0.82em; }
table { font-size: 0.9em; }
th, td { padding: 0.5em 0.8em; }
.chip { font-size: 0.85em; padding: 0.2em 0.7em; }
.verdict { font-size: 2em; }
.guide-step { padding: 1em 1.2em; margin: 1em 0; font-size: 0.95em; }
.boundary-footer { font-size: 0.88em; padding: 1em 1.2em; }
.card { padding: 1.2em; }
.card-title { font-size: 1em; }
pre { font-size: 0.85em; line-height: 1.5; }
"""
