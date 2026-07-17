# Contributing

Use small, evidence-backed changes.

Development setup:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/test_community_backend_acceptance.py -q
```

Before opening a pull request:

```bash
python -m pytest tests/test_public_packaging_docs.py -q
python -m pytest tests/rtc/test_phase0_runtime.py -q
```

Rules:

- Do not commit secrets, personal paths, bytecode, caches or private artifacts.
- Keep community features local-first and useful without cloud services.
- Commercial-only implementations must stay out of the public tree.
- New tools or plugins must respect capability leases and receipt logging.
