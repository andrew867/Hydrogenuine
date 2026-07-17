# Hydrogenuine Community

Hydrogenuine Community is a local-first governed AI workbench. It provides a real chat workspace, OpenAI-compatible and local model configuration, planning and task decomposition, workflow runs, research fixtures, document memory, capability leases, receipts and a public UI that runs on your machine.

The community edition is designed to be independently useful without Hydrogenuine cloud services. Commercial-only code such as managed tenancy, fleet administration, enterprise SSO, customer data, private policy packs and proprietary connectors is not included.

## Quick Start

Requirements:

- Python 3.10 or newer.
- Node is optional for development tooling. The public UI is static HTML/CSS/JS.
- Docker is optional.

Windows:

```powershell
.\start.ps1
```

Linux or macOS:

```bash
./start.sh
```

The scripts create a local `.venv`, install the package, generate a local `.env` if needed, start the API on `http://127.0.0.1:8000`, and serve the community UI on `http://127.0.0.1:4173`.

Default local API key:

```text
oss-demo-key
```

Stop the native services:

```powershell
.\stop.ps1
```

```bash
./stop.sh
```

Run diagnostics:

```powershell
.\doctor.ps1
```

```bash
./doctor.sh
```

Run the deterministic no-network demo:

```powershell
.\demo.ps1
```

```bash
./demo.sh
```

## Docker

Build and run the API plus static UI:

```bash
docker compose up --build
```

Open:

- UI: `http://127.0.0.1:4173`
- API health: `http://127.0.0.1:8000/healthz`

The compose file uses local volumes and does not require Postgres, Redis or cloud services for the community demo path.

## What Works

- Governed chat with deterministic safe local fallback.
- Model provider discovery for stub, OpenAI-compatible, Ollama, LM Studio and vLLM-style endpoints.
- Editable plans and approval receipts.
- Workflow creation and deterministic local run artifacts.
- Research fixture reports with claim boundaries.
- Text document ingestion, chunking and citation-style query hits.
- Persistent memory candidates with explicit accept/edit/delete lifecycle and no action authority.
- Capability lease request, approval, revocation and default-deny tool execution.
- Receipt chain and local export.
- Public static UI routes for chat, workflows, research, documents, memory, approvals, receipts, settings, onboarding and diagnostics.

## Local Data

By default data is stored under `.hg_community` in the repo root. Override it with:

```bash
HG_COMMUNITY_DATA_DIR=/path/to/data
```

Telemetry is off by default. Network calls only occur when you configure a non-stub model or run a command that explicitly uses the network.

## Model Setup

The deterministic stub provider works without credentials. To use a local or OpenAI-compatible endpoint, set the relevant values in the UI settings or environment:

```bash
HG_MODEL_PROVIDER=openai-compatible
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_MODEL=local-model
```

Do not put secrets in committed files. Use your shell environment or a local `.env` that is excluded from git.

## Verification Commands

```bash
python -m pytest tests/test_community_backend_acceptance.py -q
python -m pytest tests/test_public_packaging_docs.py -q
python -m pytest tests/rtc/test_phase0_runtime.py -q
python docs/planning/oss-release/full-tilt-run/tools/verify_no_bytecode_only_export.py .
```

## Repository Map

- `hg_gateway/`: FastAPI gateway and community API routes.
- `hg_llm/`: model adapter surface.
- `hg_runtime/`, `hg_gpp/`, `hg_hal/`, `hg_soar/`, `hg_ueak/`, `hg_oea/`, `hg_lease/`: governance and runtime packages retained for public-safe local operation.
- `community_ui/`: static public UI.
- `docs/community/`: public documentation.
- `examples/`: deterministic demo fixtures and extension examples.
- `tests/`: acceptance, packaging and runtime tests.

## License

Hydrogenuine Community source is released under Apache-2.0 unless a file says otherwise. See `LICENSE`, `NOTICE` and `THIRD_PARTY_NOTICES.md`.
