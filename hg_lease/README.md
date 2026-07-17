# hg_lease — Conversationally Minted Capability Leasing

An operator should not have to repeat the same low-risk decision every time an
agent performs a familiar action. `hg_lease` turns an operator-confirmed
natural-language policy into a **bounded, inspectable, revocable, expiring
capability lease** — while conversational memory never becomes authority.

```text
conversation -> policy draft -> operator-visible canonical form
  -> explicit confirmation -> GPP lease minting
  -> context and situation evaluation -> restrictive vetoes
  -> external-action crossing -> immutable receipt
  -> renewal, expiry, revocation, or supersession
```

## Quick start (local, no hardware, no network)

```bash
# 1. Setup wizard: local profile, DEV trust root, conservative defaults,
#    sample policy, self-test.
python -m hg_lease.setup_wizard --home ~/.hg_lease

# 2. Run the simulated west-kitchen-window demo (all twelve proof beats).
python -m hg_lease.demos.window_demo

# 3. Run the synthetic instrument-calibration demo.
python -m hg_lease.demos.instrument_demo

# 4. Run the test suite (unit, lifecycle, invariant-attack, demo proofs).
python -m pytest tests/lease -q

# Or in Docker (non-root, no network, persistent /data volume):
docker compose -f docker/lease-demo/docker-compose.yml up --build
```

## Architecture (see docs/adr/ADR-CCL-001)

| Module | Responsibility |
|---|---|
| `policy.py` | Canonical typed policy AST (`hg.policy.v1`): comparisons, boolean ops, time windows, numeric limits with explicit units, named situation facts. No `eval`, no templates; unknown condition types are rejected. |
| `compiler.py` | Structured conversational draft → `CanonicalPolicy` or `ClarificationNeeded`. Ambiguity asks; it never defaults permissively. |
| `lease.py` | `hg.lease.v1` lifecycle state machine (DRAFT→…→REVOKED), table-driven, idempotent per event id, terminal states sticky. |
| `stores.py` | Four separated stores: context (authority structurally `NONE`), lease, situation (typed expiring facts), receipts (append-only hash chain). |
| `evaluator.py` | Deterministic decision function; fail-closed on unknown/stale facts, unit mismatch, replay, monotonic clock regression, policy-hash mismatch. |
| `gpp_bridge.py` | `LeaseAuthority`: mints leases only from exact-hash operator confirmations; every ALLOW mints a **short-lived GovernedPermit through `hg_gpp.PermitAuthority`** — GPP stays the single authority path. |
| `invalidation.py` | Event-driven invalidation: suspend first, re-evaluate, resume or stay down; close obligations emitted on trigger facts. |
| `operator.py` | Dashboard: active leases, why-did-you-act/ask, revoke one/all, renewal drafts, measured decision-saturation report. |
| `delegation.py` | Roles + deny-wins conflicts; delegation strictly inside the parent envelope; no re-delegation; parent revocation cascades. |
| `adapters.py` / `oea_crossing.py` | Simulated adapters (`SIMULATED` provenance on every result) behind a crossing that verifies + single-use-consumes the GPP permit before dispatch. Hardware adapters are refused unless explicitly enabled. |
| `setup_wizard.py` | Local profile, Ed25519 dev trust root (`cryptography` library), conservative defaults, self-test, diagnostics. |

## Policy language reference (short)

A condition is one of:

- `{"type": "fact", "fact_name": str, "op": "lt|le|gt|ge|eq|ne|in|not_in", "value": any, "unit": str|null}`
- `{"type": "time_window", "start": "HH:MM", "end": "HH:MM"}` (may cross midnight)
- `{"type": "all_of"|"any_of", "children": [...]}`
- `{"type": "not", "child": ...}` — note: `not(unknown fact)` still denies

Numeric limits bind action parameters: `{"parameter": "opening", "max_value": 100.0, "unit": "mm"}` —
requests must carry `{"value": ..., "unit": "mm"}`; unit mismatch denies.

Risk classes: `LOW` leases freely; `MODERATE` needs explicit opt-in at compile
time; `HIGH`/`CRITICAL` are not leaseable unless a dedicated local policy says
otherwise. Unknown facts follow `unknown_fact_policy` (`DENY` default, `ASK`
optional).

## Threat model (summary)

Attacks the test suite proves are closed (`tests/lease/test_invariants.py`):
context→authority confusion, restriction→grant upgrade, revocation survival,
superseded-lease execution, request replay, permit double-consume, stale
permits, delegation amplification, invalidation races, receipt rewriting,
private-module import into the OSS core, and default network egress.

## Privacy

Everything is local-first. The context store supports export,
delete-by-subject, and retention-class purges. Receipts are append-only local
records. There is no external telemetry of any kind.

## Commercial boundary

The OSS core exposes interfaces only. The dev signer is explicitly labelled
non-assurance; `operator_profile.json` has an `assurance_provider` slot where
commercial implementations (fingerprinting, attestation, fleet control) can
plug in. None of their implementation exists in this tree —
`test_i10_no_private_implementation_in_hg_lease` enforces it mechanically.

## Honest limits

- All demos and adapters are SIMULATED/SYNTHETIC. No physical device was or
  can be controlled by this package as shipped.
- The GPP composition uses the repository's existing fixture capability
  (`cap.oea_stub_log`) as the execution capability; production deployments
  register their own capability + authority-chain decisions.
- Formal (TLA+) modelling of the lease state machine is future work; current
  verification is test-based (exhaustive transition table + seeded fuzz).
