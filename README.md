# Hydrogenuine Community

### Local AI with receipts, boundaries, and operator review.

Hydrogenuine Community is an open-source, local-first governed AI workbench. It combines persistent multi-chat, local model support, document memory, plans, workflows, approvals, capability leases, and cryptographic receipts in one self-contained runtime.

Run it without cloud services. Start in deterministic demo mode with no model server, or connect LM Studio and other OpenAI-compatible local endpoints without an API key.

> **The model proposes. The runtime disposes.**

Hydrogenuine uses **Artificial Governed Intelligence** to describe AI workflows constrained by explicit authority, evidence boundaries, receipts, and human review. It is not a claim of general intelligence.

## See it work offline

[![Hydrogenuine Community offline three-model evidence review](docs/assets/multimodel-research-demo-poster.png)](docs/assets/multimodel-research-demo.webm)

This accelerated walkthrough shows a complete local evidence-review workflow:

1. `qwen2.5-1.5b-instruct` reviews a hashed repository source pack.
2. `smollm2-1.7b` independently reviews the same evidence.
3. `qwen3-4b-2507` checks both analyses against the sources and produces one bounded candidate synthesis.
4. Hydrogenuine records model identities, source hashes, response hashes, timestamps, usage, and five linked receipts.

All inference in this demonstration ran through LM Studio on `127.0.0.1:1234`. No API key, paid inference, or cloud model was used. Inspect the [public proof bundle](docs/reports/oss_multimodel_demo/proof) or read the [multi-model research guide](docs/community/multimodel_research.md).

The synthesis remains marked **review required**. Model agreement does not grant authority. This is multi-model evidence through one local endpoint, not multi-provider evidence or independent factual verification.

## Quick start

Requirements:

- Python 3.10 or newer
- Windows, Linux, or macOS
- Node.js is not required for the Community UI
- Docker is optional

### Windows PowerShell

```powershell
git clone https://github.com/andrew867/Hydrogenuine.git
cd Hydrogenuine
.\start.ps1
```

### Linux or macOS

```bash
git clone https://github.com/andrew867/Hydrogenuine.git
cd Hydrogenuine
./start.sh
```

Open `http://127.0.0.1:4173`.

The launcher creates an isolated virtual environment, installs the package, writes a safe local configuration, starts the loopback-only API, and stores Community data in `.hg_community`. Demo mode needs no gateway key, cloud key, LM Studio, or private service. Stop it with `.\stop.ps1` on Windows or `./stop.sh` on Linux and macOS.

## Choose how Hydrogenuine runs

The first-run wizard offers four explicit modes:

| Mode | Purpose | API key required |
| --- | --- | --- |
| `demo` | Deterministic offline evaluation and product walkthrough | No |
| `local` | LM Studio or another local OpenAI-compatible endpoint | No |
| `cloud` | An explicitly selected external model provider | Only for that provider |
| `private` | Configuration boundary for the separate private/commercial stack | Depends on that deployment |

```bash
hg init
hg doctor --self-test
hg config show --redacted
hg demo
```

`hg init` writes configuration, never secret values. `hg doctor` distinguishes gateway access from model-provider credentials and reports optional providers as unavailable rather than declaring the whole system broken.

## Connect LM Studio

1. Start the LM Studio local server.
2. Load the model or models you want to use.
3. Confirm the OpenAI-compatible endpoint, normally `http://127.0.0.1:1234/v1`.
4. Configure and validate Hydrogenuine:

```powershell
.\.venv\Scripts\hg.exe init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model local-model --non-interactive
.\.venv\Scripts\hg.exe doctor --self-test
.\start.ps1
```

```bash
.venv/bin/hg init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model local-model --non-interactive
.venv/bin/hg doctor --self-test
./start.sh
```

Hydrogenuine validates the local `/models` endpoint before saving an active local configuration. Use `--skip-validation` only when preparing configuration before the model server is available.

## Persistent multi-chat

The Community UI supports creating, selecting, branching, and resuming independent conversations. Native and Docker launchers use SQLite so chat history survives gateway restarts.

The same lifecycle is available from the CLI:

```bash
hg chat new --title "Local model testing"
hg chat new --title "Research notes"
hg chat list
hg chat resume CHAT_ID
hg chat resume CHAT_ID --message "Continue from the saved context."
```

Running `hg chat resume` without an ID resumes the last chat selected by the CLI. See the [multi-chat guide](docs/community/multi_chat.md) for branching, persistence, and recovery details.

## Governed evidence review

The Research screen sends the same hashed source pack to two or more independent analyst models. A distinct synthesis model then receives the sources and analyst outputs and produces one candidate conclusion.

Each run records:

- requested and resolved model identities;
- source paths, sizes, and SHA-256 hashes;
- prompt and response hashes for every model call;
- provider-reported token usage where available;
- an ordered execution timeline;
- receipts for start, each analysis, synthesis, and completion;
- a stable hash over the completed run.

Analyst outputs are untrusted interpretations, not sources. A completed workflow proves that the recorded execution occurred against the named evidence. It does not prove that the generated conclusion is true.

## Community capabilities

- Persistent multi-chat with branching and deterministic offline fallback
- LM Studio and generic local OpenAI-compatible endpoint support
- Optional external-provider configuration through environment variables
- Multi-model evidence review with candidate synthesis and receipt export
- Editable plans and workflow fixtures
- Document ingestion and quarantined candidate memory
- Approval records and bounded capability leases
- Default-deny tool execution
- Local receipt chains and proof export
- Onboarding, diagnostics, model, tool, and data settings
- Telemetry disabled by default

Provider availability never grants authority. Optional integrations can be unavailable while the local Community runtime remains usable.

## Configuration and secrets

Native demo and local-model modes use loopback-only no-key access. Docker or an explicitly selected gateway `api-key` mode may use a local transport credential to protect the HTTP API. That gateway credential is not a model-provider key.

External-provider secrets remain in environment variables. They are not written by `hg init` and are redacted by `hg config show --redacted`.

See [CONFIGURATION.md](CONFIGURATION.md) for every supported mode and field.

## Docker

```bash
docker compose up --build
```

Open:

- Community UI: `http://127.0.0.1:4173`
- API health: `http://127.0.0.1:8000/healthz`

Docker Compose uses a local transport token between the shipped browser UI and gateway. The deterministic demo does not require a model-provider key.

## Documentation

- [Installation](INSTALL.md)
- [Quick start](docs/community/quickstart.md)
- [Configuration](CONFIGURATION.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Multi-chat and sessions](docs/community/multi_chat.md)
- [Multi-model research](docs/community/multimodel_research.md)
- [Community API](docs/community/api.md)
- [Security and privacy](docs/community/security_privacy.md)

## Verification

```bash
python -m pytest tests/test_oss_first_run_cli.py tests/test_oss_first_run_gateway.py -q
python -m pytest tests/test_community_backend_acceptance.py tests/test_public_packaging_docs.py -q
python tools/green_oss_first_run_ux_ready.py
python tools/green_oss_multimodel_demo_ready.py
```

The readiness gates cover their named Community workflows and public artifacts. A passing gate is scoped evidence, not a production-readiness, enterprise-readiness, security-certification, or compliance claim.

## Project scope

Hydrogenuine Community is a public pre-alpha. It is independently useful without Hydrogenuine cloud services.

Managed tenancy, fleet administration, enterprise SSO, private policy packs, customer data, proprietary connectors, and the private/commercial control stack are outside this repository.

## Local data

Native startup stores configuration, chats, receipts, and Community data under `.hg_community`, which is excluded from git. Set `HG_COMMUNITY_DATA_DIR` to select another location.

## Repository map

- `hg_cli/`: setup, diagnostics, redacted configuration, demo, and chat commands
- `hg_gateway/`: FastAPI gateway and Community routes
- `hg_llm/`: local and optional external model adapters
- `hg_runtime/`, `hg_gpp/`, `hg_hal/`, `hg_soar/`, `hg_ueak/`, `hg_oea/`, `hg_lease/`: public governance and runtime packages
- `community_ui/`: static Community UI
- `docs/community/`: public user documentation
- `tests/`: acceptance, first-run, packaging, and runtime tests

## License

Hydrogenuine Community is released under the Apache License 2.0 unless a file states otherwise. See [LICENSE](LICENSE), [NOTICE](NOTICE), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
