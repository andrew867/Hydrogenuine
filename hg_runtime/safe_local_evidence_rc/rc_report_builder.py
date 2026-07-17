"""SLE-RC report builder helpers."""

from __future__ import annotations

from pathlib import Path


def build_phase_report(*, title: str, verdict: str, proof_bundle: str, sections: list[str]) -> str:
    body = "\n\n".join(sections)
    return f"""# {title}

- Verdict: `{verdict}`

{body}

## Proof Bundle

`{proof_bundle}`
"""


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
