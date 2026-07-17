"""Pretty ANSI renderer for zero CLI output.

Uses rich if available, falls back to plain text.
No external network. No unsafe claims.
"""

from __future__ import annotations

import io

_HAS_RICH = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    pass

BOUNDARY_LINE = "Source != truth | Screenshot != proof | Model output != truth | No self-authorization"


def _plain_proof_summary(result: dict) -> str:
    d = result.get("data", {})
    o = d.get("overview", {})
    inv = d.get("proof_inventory", {})
    lines = [
        "=== PROOF SUMMARY ===",
        "",
        f"  Gate verdict:       {o.get('gate_verdict', 'UNKNOWN')} ({o.get('gate_checks_passed', 0)}/{o.get('gate_checks_total', 0)})",
        f"  Cycles:             {o.get('cycles', 0)}",
        f"  Sources attempted:  {o.get('sources_attempted', 0)}",
        f"  Fetches succeeded:  {o.get('successful_fetches', 0)}",
        f"  Fetches failed:     {o.get('failed_fetches', 0)}",
        f"  Screenshots:        {o.get('screenshots_captured', 0)}",
        f"  Model inferences:   {o.get('model_successes', 0)}/{o.get('model_attempts', 0)}",
        f"  Contradictions:     {o.get('contradictions', 0)}",
        f"  Quarantined:        {o.get('quarantine_entries', 0)}",
        f"  Promotions:         {o.get('promotions_count', 0)}",
        f"  External effects:   {o.get('external_effects_count', 0)}",
        f"  Public claim flags: {o.get('public_claim_flags', 0)}",
        f"  STOP/PANIC:         {d.get('stop_panic_status', 'not_triggered')}",
        "",
        f"  Total receipts:     {sum(v for v in inv.values() if isinstance(v, int))}",
        "",
        BOUNDARY_LINE,
    ]
    return "\n".join(lines)


def _plain_table(result: dict, items_key: str, columns: list[tuple[str, str]]) -> str:
    d = result.get("data", {})
    items = d.get(items_key, [])
    if not items:
        return f"No {items_key} found.\n\n{BOUNDARY_LINE}"
    header = " | ".join(f"{label:>{width}}" if width.isdigit() else f"{label:<{int(width[:-1]) if width[:-1].isdigit() else 20}}" for label, key, width in columns)
    lines = [f"=== {result.get('command', '').upper()} ({len(items)}) ===", "", header, "-" * len(header)]
    for item in items:
        row = " | ".join(
            f"{str(item.get(key, '')):>{width}}" if width.isdigit() else f"{str(item.get(key, '')):<{int(width[:-1]) if width[:-1].isdigit() else 20}}"
            for label, key, width in columns
        )
        lines.append(row)
    lines.extend(["", BOUNDARY_LINE])
    return "\n".join(lines)


def _rich_proof_summary(result: dict) -> str:
    d = result.get("data", {})
    o = d.get("overview", {})

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=80)

    gv = o.get("gate_verdict", "UNKNOWN")
    gate_style = "bold green" if gv == "GREEN" else "bold red"
    verdict_text = Text(f"Gate: {gv} ({o.get('gate_checks_passed', 0)}/{o.get('gate_checks_total', 0)})")
    verdict_text.stylize(gate_style)

    table = Table(title="Proof Summary", show_header=True, header_style="bold")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    rows = [
        ("Cycles", o.get("cycles", 0)),
        ("Sources attempted", o.get("sources_attempted", 0)),
        ("Fetches succeeded", o.get("successful_fetches", 0)),
        ("Fetches failed", o.get("failed_fetches", 0)),
        ("Screenshots", o.get("screenshots_captured", 0)),
        ("Model inferences", f"{o.get('model_successes', 0)}/{o.get('model_attempts', 0)}"),
        ("Contradictions", o.get("contradictions", 0)),
        ("Quarantined", o.get("quarantine_entries", 0)),
        ("Promotions", o.get("promotions_count", 0)),
        ("External effects", o.get("external_effects_count", 0)),
        ("Public claim flags", o.get("public_claim_flags", 0)),
        ("STOP/PANIC", d.get("stop_panic_status", "not_triggered")),
    ]
    for label, value in rows:
        val_str = str(value)
        style = ""
        if label == "Promotions" and value == 0:
            style = "green"
        elif label == "External effects" and value == 0:
            style = "green"
        elif label in ("Fetches failed", "Contradictions") and value and int(str(value).split("/")[0]) > 0:
            style = "yellow"
        table.add_row(label, val_str, style=style)

    console.print(verdict_text)
    console.print(table)
    console.print(f"\n[dim]{BOUNDARY_LINE}[/dim]")

    return buf.getvalue()


def _rich_sources(result: dict) -> str:
    d = result.get("data", {})
    items = d.get("sources", [])

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120)

    table = Table(title=f"Sources ({len(items)})", show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=14)
    table.add_column("URL", max_width=40)
    table.add_column("Status", width=8)
    table.add_column("HTTP", justify="right", width=5)
    table.add_column("Hash", style="dim", width=18)

    for s in items:
        status = s.get("status", "")
        style = "green" if status == "success" else "red"
        table.add_row(
            str(s.get("source_candidate_id", "")),
            str(s.get("url", ""))[:40],
            Text(status, style=style),
            str(s.get("http_status", "")),
            str(s.get("content_hash", "")),
        )

    console.print(table)
    console.print(f"\n[dim]{BOUNDARY_LINE}[/dim]")
    return buf.getvalue()


def _rich_witnesses(result: dict) -> str:
    d = result.get("data", {})
    items = d.get("witnesses", [])

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120)

    table = Table(title=f"Model Witnesses ({len(items)})", show_header=True, header_style="bold")
    table.add_column("Cycle", width=30)
    table.add_column("Model", width=24)
    table.add_column("Status", width=10)
    table.add_column("Fallback", width=9)
    table.add_column("Chars", justify="right", width=6)
    table.add_column("Latency", justify="right", width=8)

    for w in items:
        status = w.get("inference_status", "")
        style = "green" if status == "success" else ("yellow" if "skip" in status else "red")
        fb = "false" if not w.get("remote_fallback_used") else "TRUE"
        fb_style = "green" if fb == "false" else "bold red"
        table.add_row(
            str(w.get("cycle_id", "")),
            str(w.get("model_name", "")) or "(skipped)",
            Text(status, style=style),
            Text(fb, style=fb_style),
            str(w.get("output_chars", 0)),
            f"{w.get('latency_ms', 0)}ms",
        )

    console.print(table)
    console.print(f"\n[dim]{BOUNDARY_LINE}[/dim]")
    return buf.getvalue()


def _rich_quarantine(result: dict) -> str:
    d = result.get("data", {})
    items = d.get("quarantine_items", [])

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=100)

    if not items:
        console.print("[yellow]No quarantine items in data.[/yellow]")
    else:
        table = Table(title=f"Quarantine ({len(items)})", show_header=True, header_style="bold")
        table.add_column("Receipt", width=18)
        table.add_column("Quarantined", justify="right", width=12)
        table.add_column("Promoted", justify="right", width=10)
        table.add_column("Promotion", width=10)
        table.add_column("Timestamp", width=22)
        for q in items:
            table.add_row(
                str(q.get("receipt_id", ""))[:16],
                str(q.get("quarantined_count", 0)),
                str(q.get("promoted_count", 0)),
                Text("false", style="green"),
                str(q.get("timestamp", "")),
            )
        console.print(table)

    console.print(f"\n[dim]{BOUNDARY_LINE}[/dim]")
    return buf.getvalue()


def _plain_json_fallback(result: dict) -> str:
    import json
    lines = [f"=== {result.get('command', '').upper()} ===", ""]
    d = result.get("data", {})
    for key, val in d.items():
        if isinstance(val, (list, dict)):
            lines.append(f"  {key}: {json.dumps(val, default=str)[:200]}")
        else:
            lines.append(f"  {key}: {val}")
    lines.extend(["", BOUNDARY_LINE])
    return "\n".join(lines)


def _rich_generic(result: dict) -> str:
    import json

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=100)

    command = result.get("command", "")
    d = result.get("data", {})

    console.print(f"[bold]=== {command.upper()} ===[/bold]\n")
    for key, val in d.items():
        if isinstance(val, bool):
            style = "green" if val else "red"
            console.print(f"  [dim]{key}:[/dim] [{style}]{val}[/{style}]")
        elif isinstance(val, (int, float)):
            console.print(f"  [dim]{key}:[/dim] {val}")
        elif isinstance(val, str):
            console.print(f"  [dim]{key}:[/dim] {val}")
        elif isinstance(val, list):
            console.print(f"  [dim]{key}:[/dim] ({len(val)} items)")
        elif isinstance(val, dict):
            console.print(f"  [dim]{key}:[/dim] {json.dumps(val, default=str)[:120]}")

    console.print(f"\n[dim]{BOUNDARY_LINE}[/dim]")
    return buf.getvalue()


def _plain_overnight_summary(result: dict) -> str:
    d = result.get("data", {})
    o = d.get("overview", {})
    ts = d.get("throughput_summary", {})
    tl = d.get("telemetry_summary", {})
    integrity = d.get("integrity_manifest", {})
    receipt = d.get("receipt_completeness", {})
    inv = d.get("proof_inventory", {})
    lines = [
        "=== OVERNIGHT PROOF SUMMARY ===",
        "",
        f"  Verdict:            {o.get('verdict', 'UNKNOWN')}",
        f"  Question:           {o.get('question', '')[:60]}",
        f"  Model profile:      {o.get('model_profile', 'unknown')}",
        f"  Sources fetched:    {o.get('sources_fetched', 0)}",
        f"  Model calls:        {o.get('model_calls', 0)}",
        f"  Succeeded:          {o.get('model_calls_succeeded', 0)}",
        f"  Timed out:          {o.get('model_calls_timed_out', 0)}",
        f"  Skipped:            {o.get('model_calls_skipped', 0)}",
        f"  Claims extracted:   {o.get('claims_extracted', 0)}",
        f"  Backlog topics:     {o.get('backlog_topics', 0)}",
        f"  Promotions:         {o.get('promotions', 0)}",
        "",
    ]
    if tl:
        lines.extend([
            "  --- Telemetry ---",
            f"  Elapsed:            {tl.get('elapsed_seconds', 0):.1f}s",
            f"  Model seconds:      {tl.get('model_seconds', 0):.1f}",
            f"  STOP/PANIC:         {tl.get('stop_panic_seen', False)}",
            "",
        ])
    if integrity.get("present"):
        lines.extend([
            "  --- Integrity ---",
            f"  Files hashed:       {integrity.get('file_count', 0)}",
            f"  Combined hash:      {integrity.get('combined_hash', '')}",
            f"  Tamper evidence:    {integrity.get('tamper_evidence_only', True)}",
            "",
        ])
    if receipt.get("present"):
        lines.extend([
            "  --- Receipt Completeness ---",
            f"  Verdict:            {receipt.get('verdict', 'UNKNOWN')}",
            f"  Passed:             {receipt.get('passed', 0)}/{receipt.get('total', 0)}",
            "",
        ])

    lines.extend([
        f"  Total receipts:     {sum(v for v in inv.values() if isinstance(v, int))}",
        "",
        BOUNDARY_LINE,
    ])
    return "\n".join(lines)


def render_pretty(result: dict, *, no_color: bool = False) -> str:
    """Render a CLI result in pretty format."""
    command = result.get("command", "")

    if result.get("status") == "error":
        errors = result.get("errors", [])
        msg = f"ERROR: {errors[0]}" if errors else "ERROR: unknown"
        return f"{msg}\n\n{BOUNDARY_LINE}"

    source_type = result.get("data", {}).get("source_type", "")

    if no_color or not _HAS_RICH:
        if source_type == "overnight_proof_dir" and command == "proof-summary":
            return _plain_overnight_summary(result)
        if command == "proof-summary":
            return _plain_proof_summary(result)
        if command == "sources":
            return _plain_table(result, "sources", [("URL", "url", "40s"), ("Status", "status", "8s")])
        if command == "model-witnesses":
            return _plain_table(result, "witnesses", [("Cycle", "cycle_id", "30s"), ("Model", "model_name", "24s"), ("Status", "inference_status", "10s")])
        if command == "quarantine":
            return _plain_table(result, "quarantine_items", [("Receipt", "receipt_id", "18s"), ("Quarantined", "quarantined_count", "5"), ("Promoted", "promoted_count", "5")])
        return _plain_json_fallback(result)

    if source_type == "overnight_proof_dir" and command == "proof-summary":
        return _plain_overnight_summary(result)
    elif command == "proof-summary":
        return _rich_proof_summary(result)
    elif command == "sources":
        return _rich_sources(result)
    elif command == "model-witnesses":
        return _rich_witnesses(result)
    elif command == "quarantine":
        return _rich_quarantine(result)
    else:
        return _rich_generic(result)
