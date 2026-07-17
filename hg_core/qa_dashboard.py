"""
Generate a QA status dashboard HTML from real data: tasks, personas, overseer state, DAG runs.
Run from workspace root: python -m hg_core.qa_dashboard
Output: docs/qa/dashboard.html
"""

import json
import os
from datetime import datetime
from pathlib import Path

from hg_gateway.shared_storage import get_latest_overseer_state, list_agent_decisions, list_overseer_timeseries


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return Path(__file__).resolve().parent.parent


def _load_tasks(root: Path) -> list[dict]:
    try:
        from hg_core.job_registry import list_tasks, get_job_info
        tasks = []
        for name in list_tasks():
            info = get_job_info(name) or {}
            tasks.append({
                "name": name,
                "job_id": info.get("job_id", ""),
                "platform": info.get("platform"),
                "mode": info.get("mode"),
                "session_target": info.get("session_target", ""),
            })
        return tasks
    except Exception as e:
        return [{"error": str(e), "name": "?", "job_id": "", "platform": "", "mode": ""}]


def _load_automation_agents(root: Path) -> list[dict]:
    automation_dir = root / "memory" / "automation"
    if not automation_dir.is_dir():
        return []
    agents = []
    for path in sorted(automation_dir.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith("automation-"):
            continue
        agent_id = name.replace("automation-", "", 1)
        # Lightweight stats: count .md and DB-backed decision history
        md_count = len(list(path.glob("*.md"))) if path.is_dir() else 0
        agents.append({
            "agent_id": agent_id,
            "dir": name,
            "has_decisions": bool(list_agent_decisions(agent_id, limit=1)),
            "md_count": md_count,
        })
    return agents


def _load_overseer_latest(root: Path) -> dict | None:
    payload = get_latest_overseer_state()
    if payload is not None:
        return payload
    return None


def _load_timeseries_summary(root: Path, hours: int = 24) -> dict:
    rows = list_overseer_timeseries(hours=hours, limit=100000)
    if rows:
        return {"count": len(rows), "last_timestamp": rows[-1].get("timestamp"), "hours": hours}
    return {"count": 0, "message": "No DB-backed timeseries rows"}


def _load_dag_runs(root: Path, max_entries: int = 50) -> list[dict]:
    runs_dir = root / "memory" / "automation" / "dag_runs"
    if not runs_dir.is_dir():
        return []
    entries = []
    for path in sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if len(entries) >= max_entries:
            break
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            run_id = data.get("run_id") or path.stem
            graph_id = data.get("graph_id") or data.get("dag", {}).get("graph_id") or "?"
            status = data.get("final_status") or data.get("status") or "unknown"
            ts = data.get("started_at") or data.get("timestamp") or path.stem
            entries.append({
                "run_id": run_id,
                "graph_id": graph_id,
                "status": status,
                "timestamp": ts,
            })
        except Exception:
            entries.append({"run_id": path.stem, "graph_id": "?", "status": "error", "timestamp": ""})
    return entries


def _load_persona_names(root: Path) -> list[str]:
    personas_dir = root / "skills" / "automation" / "personas"
    if not personas_dir.is_dir():
        return []
    names = set()
    # From .backups/<name>/...
    backups = personas_dir / ".backups"
    if backups.is_dir():
        for d in backups.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                names.add(d.name)
    # Top-level dirs that look like persona names (e.g. default or named)
    for d in personas_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            names.add(d.name)
    return sorted(names)


def _build_html(root: Path, out_path: Path) -> None:
    tasks = _load_tasks(root)
    agents = _load_automation_agents(root)
    overseer = _load_overseer_latest(root)
    timeseries = _load_timeseries_summary(root)
    dag_runs = _load_dag_runs(root)
    personas = _load_persona_names(root)

    ts_str = datetime.now().isoformat(timespec="seconds")
    overseer_agents = ""
    if overseer and isinstance(overseer.get("agents"), dict):
        rows = []
        for aid, adata in overseer["agents"].items():
            mode = adata.get("mode", "")
            platform = adata.get("platform", "")
            rows.append(f"<tr><td>{_esc(aid)}</td><td>{_esc(platform)}</td><td>{_esc(mode)}</td></tr>")
        overseer_agents = "<table><tr><th>Agent</th><th>Platform</th><th>Mode</th></tr>" + "".join(rows) + "</table>"
    else:
        overseer_agents = "<p>No latest state (or no agents key). Run overseer to populate.</p>"

    task_rows = []
    for t in tasks:
        err = t.get("error")
        if err:
            task_rows.append(f"<tr><td colspan='4' class='error'>{_esc(err)}</td></tr>")
        else:
            task_rows.append(
                f"<tr><td>{_esc(t['name'])}</td><td>{_esc(str(t.get('platform') or ''))}</td>"
                f"<td>{_esc(str(t.get('mode') or ''))}</td><td>{_esc(t.get('session_target', ''))}</td></tr>"
            )
    tasks_table = (
        "<table><tr><th>Task</th><th>Platform</th><th>Mode</th><th>Session target</th></tr>"
        + "".join(task_rows) + "</table>"
    )

    agent_rows = []
    for a in agents:
        agent_rows.append(
            f"<tr><td>{_esc(a['agent_id'])}</td><td>{a['md_count']}</td>"
            f"<td>{'Yes' if a['has_decisions'] else 'No'}</td></tr>"
        )
    agents_table = (
        "<table><tr><th>Agent ID</th><th>MD files</th><th>decision ledger</th></tr>"
        + "".join(agent_rows) + "</table>"
    )

    dag_rows = []
    for r in dag_runs:
        dag_rows.append(
            f"<tr><td>{_esc(r['run_id'])}</td><td>{_esc(r['graph_id'])}</td>"
            f"<td>{_esc(r['status'])}</td><td>{_esc(r['timestamp'])}</td></tr>"
        )
    if not dag_rows:
        dag_rows.append("<tr><td colspan='4'>No DAG runs found. Run: python -m hg_core.run_dag memory/automation/dags/linear_three_steps.json</td></tr>")
    dag_table = (
        "<table><tr><th>Run ID</th><th>Graph</th><th>Status</th><th>Time</th></tr>"
        + "".join(dag_rows) + "</table>"
    )

    persona_list = ", ".join(_esc(p) for p in personas) if personas else "None found"
    timeseries_msg = f"Entries (last {timeseries.get('hours', 24)}h): {timeseries.get('count', 0)}"
    if timeseries.get("last_timestamp"):
        timeseries_msg += f" · Last: {timeseries['last_timestamp']}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Hydrogenuine QA Dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1rem 2rem; background: #f5f5f5; }}
h1 {{ color: #111; }}
h2 {{ color: #333; margin-top: 1.5rem; border-bottom: 1px solid #ccc; }}
table {{ border-collapse: collapse; background: #fff; margin: 0.5rem 0; }}
th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ background: #e8e8e8; }}
.meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1rem; }}
.error {{ color: #c00; }}
section {{ background: #fff; padding: 1rem; margin: 1rem 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
</style>
</head>
<body>
<h1>Hydrogenuine QA Dashboard</h1>
<p class="meta">Generated at {ts_str} · Real data from workspace</p>

<section>
<h2>Registered tasks (job registry)</h2>
{tasks_table}
</section>

<section>
<h2>Automation agents (memory/automation)</h2>
<p>Directories <code>automation-*</code> and their activity.</p>
{agents_table}
</section>

<section>
<h2>Overseer latest state</h2>
<p>From <code>memory/overseer/latest_state.json</code>. Timeseries: {timeseries_msg}</p>
{overseer_agents}
</section>

<section>
<h2>DAG runs</h2>
<p>From <code>memory/automation/dag_runs/</code> (recent).</p>
{dag_table}
</section>

<section>
<h2>Personas (skills/automation/personas)</h2>
<p>Names found from persona directories / backups.</p>
<p>{persona_list}</p>
</section>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


def _esc(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def get_data(root: Path) -> dict:
    """Return dashboard data as dict (for JSON output)."""
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": _load_tasks(root),
        "agents": _load_automation_agents(root),
        "overseer_latest": _load_overseer_latest(root),
        "timeseries_summary": _load_timeseries_summary(root),
        "dag_runs": _load_dag_runs(root),
        "personas": _load_persona_names(root),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Hydrogenuine QA dashboard (JSON or HTML)")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    parser.add_argument("--html", action="store_true", help="Write HTML file (default if no --json)")
    parser.add_argument("-o", "--out", default=None, help="Output path for HTML (default: docs/qa/dashboard.html)")
    args = parser.parse_args()
    root = _workspace_root()
    if args.json:
        import json as _json
        print(_json.dumps(get_data(root), indent=2))
        return
    out = Path(args.out) if args.out else root / "docs" / "qa" / "dashboard.html"
    _build_html(root, out)
    try:
        rel = out.relative_to(Path(os.getcwd()))
    except ValueError:
        rel = out
    print(f"Dashboard written to: {rel}")


if __name__ == "__main__":
    main()
