"""Live-local reasoning-model handling: output classification, final-answer retry,
per-model policy, and compact prompt templates.

Reasoning trace is never the final answer. Reasoning-only is YELLOW, not RED.
Forbidden models are refused even when reachable. No tools, no live effects, no
remote fallback.
"""
