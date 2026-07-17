"""Dashboard summary helpers."""

from __future__ import annotations

from collections import Counter


def summarize_review_statuses(statuses: list[dict]) -> dict[str, int]:
    return dict(Counter(row["review_status"] for row in statuses))


def render_dashboard_markdown(dashboard: dict, review_statuses: list[dict]) -> str:
    lines = [
        "# Operator Packet Dashboard",
        "",
        "This dashboard is not operator approval.",
        "This dashboard is not truth.",
        "This dashboard cannot authorize action or tools.",
        "",
        f"- Dashboard ID: `{dashboard['dashboard_id']}`",
        f"- Claim packets: {dashboard['claim_packet_count']}",
        f"- Second-source results: {dashboard['second_source_result_count']}",
        f"- Contradiction packets: {dashboard['contradiction_packet_count']}",
        "",
        "## Review Status Summary",
        "",
    ]
    for status, count in sorted(dashboard["review_status_summary"].items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Packet Review Statuses", ""])
    for row in review_statuses:
        lines.append(f"- `{row['packet_id']}` / `{row['claim_id']}`: `{row['review_status']}`")
    return "\n".join(lines) + "\n"
