# Offline multi-model research test report

## Live run

- Research ID: `mmr_686dbc808ede`
- Created: `2026-08-21T00:49:35Z`
- Completed: `2026-08-21T01:23:03Z`
- Elapsed wall time: 33 minutes 28 seconds
- Run SHA-256: `bf33605fd4fe0352188dd779a265e0f452a373248b668c535bb065bc864e025d`
- Source-pack SHA-256: `11dc57c9fab94938ebf1563044bf03bccb63691277e334d4c0a8a6ab2e3d1a34`
- Receipts: 5
- Browser console errors in the completed walkthrough: 0

Model call timings reported by the local provider:

| Stage | Resolved model | Latency |
| --- | --- | ---: |
| Analyst A | `qwen2.5-1.5b-instruct` | 477.963 s |
| Analyst B | `smollm2-1.7b` | 396.437 s |
| Candidate synthesis | `qwen3-4b-2507` | 1,133.039 s |

## Proof verification

The exporter verified:

- completed status;
- two analyst outputs;
- three distinct requested model IDs;
- source-pack hash;
- stable run hash;
- both analyst response hashes;
- synthesis response hash;
- all receipt hashes;
- absence of secret-shaped values in the run.

Proof verdict: `VERIFIED_SCOPED_RESEARCH_RUN`.

## Output-quality boundary

The run proves orchestration and receipt integrity, not answer quality. Analyst A reached its token limit before finishing all requested sections. Analyst B returned a short authentication-error object instead of the requested review. The synthesis model produced the requested four sections and citations, but the UI deliberately labels it a candidate requiring review. No model output was edited for the proof.

## Automated compatibility tests

Command scope:

`tests/test_multimodel_research.py`, `tests/test_oss_first_run_gateway.py`, `tests/test_community_backend_acceptance.py`, and `tests/test_hg_llm_registry.py`.

Result: 22 passed, 1 skipped. The skipped test is the paid OpenAI smoke, which now requires both `HG_LLM_LIVE=1` and `HG_ALLOW_PAID_PROVIDER_TESTS=1`. Cloud credentials were removed from the successful test process.

The final gate result is recorded separately in `GREEN_OSS_MULTIMODEL_DEMO_READY.json`.
