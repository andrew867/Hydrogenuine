# Multi-model research

Hydrogenuine Community can run a bounded evidence review with two or more independent analyst models and a different conclusion model.

The shipped demonstration runs offline through LM Studio using three distinct local model families:

1. `qwen2.5-1.5b-instruct` reviews the source pack as an evidence auditor.
2. `smollm2-1.7b` reviews the same source pack as a skeptical replication reviewer.
3. `qwen3-4b-2507` receives the source pack and both completed analyses, checks the analyses against the sources, and produces one bounded conclusion.

The two analysts do not receive each other's output. The conclusion model does. A model name, agreement between models, or a completed run does not grant authority and does not establish that a claim is true.

## Configure the local LM Studio run

No API key, cloud account, or paid inference is required. Start LM Studio's local server on port 1234 and make the three selected models available. LM Studio may load them ahead of time or through its local just-in-time model loading.

```powershell
.\.venv\Scripts\hg.exe init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model qwen2.5-1.5b-instruct --non-interactive
.\.venv\Scripts\hg.exe doctor
.\start.ps1
```

```bash
.venv/bin/hg init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model qwen2.5-1.5b-instruct --non-interactive
.venv/bin/hg doctor
./start.sh
```

Open `http://127.0.0.1:4173/#/research`, review the question and model route, then select **Run independent review**.

Local CPU inference can take many minutes. Hydrogenuine does not retry these calls automatically. If the browser reaches its 30-minute display window while the backend is still working, reload the Research screen to reconnect to the persisted run.

## What is receipted

The run record includes:

- requested and provider-resolved model IDs;
- source paths, byte counts, and SHA-256 hashes;
- one prompt hash and one response hash per model call;
- provider-reported token usage where available;
- a timestamped stage timeline;
- receipt IDs for the start, each analysis, the synthesis, and completion;
- one SHA-256 hash over the stable run record.

The proof exporter verifies those hashes and writes a public-safe bundle:

```bash
python tools/export_multimodel_research_proof.py \
  --data-dir .hg_community \
  --output docs/reports/oss_multimodel_demo/proof
```

The bundle proves that the recorded models completed this scoped workflow against the named source pack. It is not independent factual verification, provider diversity, a production-readiness claim, an enterprise-readiness claim, a security certification, or a compliance claim.

## Current boundary

The public demonstration is local multi-model evidence through one LM Studio endpoint. Hydrogenuine's broader adapter layer supports optional provider configurations, but this demonstration must not be described as multi-provider until an equivalent receipted run has been completed and reviewed across more than one provider.
