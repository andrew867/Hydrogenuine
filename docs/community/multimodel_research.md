# Multi-model research

Hydrogenuine Community can run a bounded evidence review with two or more independent analyst models and a different conclusion model.

The shipped demonstration uses one provider and three distinct model IDs:

1. `gpt-4.1-mini` reviews the source pack as an evidence auditor.
2. `o4-mini` reviews the same source pack as a skeptical replication reviewer.
3. `gpt-5-mini` receives the source pack and both completed analyses, checks the analyses against the sources, and produces one bounded conclusion.

The two analysts do not receive each other's output. The conclusion model does. A model name, agreement between models, or a completed run does not grant authority and does not establish that a claim is true.

## Configure the optional cloud run

The default demo, local chat, multi-chat, documents, workflows, memory, approvals, and receipts remain usable without a cloud key. A key is required only after selecting this cloud-backed research run.

Set the key in the shell that will launch Hydrogenuine. Do not write its value into the repository or configuration file.

```powershell
$env:OPENAI_API_KEY = "your-key"
.\.venv\Scripts\hg.exe init --force --mode cloud --provider openai --model gpt-5-mini --key-env OPENAI_API_KEY --non-interactive
.\.venv\Scripts\hg.exe doctor
.\start.ps1
```

```bash
export OPENAI_API_KEY="your-key"
.venv/bin/hg init --force --mode cloud --provider openai --model gpt-5-mini --key-env OPENAI_API_KEY --non-interactive
.venv/bin/hg doctor
./start.sh
```

Open `http://127.0.0.1:4173/#/research`, review the question and model route, then select **Run independent review**.

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

The public demonstration supports an OpenAI-backed route because that is the live route tested for the recorded evidence. Hydrogenuine's broader adapter layer supports other provider configurations, but this demonstration must not be described as multi-provider until an equivalent receipted run has been completed and reviewed across more than one provider.
