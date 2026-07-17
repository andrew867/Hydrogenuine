from __future__ import annotations


CAPABILITY = "example.echo"


def run(payload: dict) -> dict:
    """Pure example adapter. Host runtimes must enforce leases before calling."""
    text = str(payload.get("text", ""))
    return {"capability": CAPABILITY, "output": text, "side_effects": []}
