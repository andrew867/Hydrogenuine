# Offline multi-model research implementation

## Outcome

Hydrogenuine Community now runs the shipped multi-model research demonstration through a loopback LM Studio endpoint by default. Basic and demo features do not require LM Studio. The Research screen requires LM Studio only when the user selects the local multi-model run.

## Runtime path

- Provider label: `lm-studio`
- Adapter runtime: `vllm` through the OpenAI-compatible protocol
- Endpoint: `http://127.0.0.1:1234/v1`
- Credential: none
- Analyst A: `qwen2.5-1.5b-instruct`
- Analyst B: `smollm2-1.7b`
- Candidate synthesis: `qwen3-4b-2507`

Local research endpoints are restricted to loopback HTTP URLs with an explicit port. Remote URLs are rejected. The route probes `/models` before accepting a run and reports an unavailable optional provider without implying that the rest of Hydrogenuine is broken.

## Long-running local inference fix

The first recorded attempt exposed a local-runtime defect: a 120-second provider timeout combined with retries repeatedly cancelled valid CPU inference. The provider adapter now accepts request-scoped timeout and retry settings. Multi-model local research uses one 1,800-second bounded attempt per model and no automatic retry. The UI polling window increased from four minutes to 30 minutes and tells users to reload to reconnect if a run continues longer.

## Claim handling

The completed synthesis is displayed as a candidate with `review required`, not as an approved fact. This matters because one analyst returned only a copied authentication error and another stopped at its output limit. Their outputs remain in the proof rather than being hidden or rewritten.

This implementation does not establish production readiness, provider diversity, factual correctness, enterprise readiness, security certification, or compliance.
