# Hydrogenuine

Hydrogenuine is a governed AI work system for supervised chat, multi-agent execution, document-driven workflows, and operator oversight. It provides the infrastructure layer that makes autonomous agent operation safe, auditable, and provable; replacing "trust me" with verifiable guarantees.

---

## What It Is

Most agent frameworks optimize for task completion. Hydrogenuine optimizes for trust. Actions become tamper-evident evidence. Outputs are published as checkable artifacts. Governance contracts define who can approve what. Continuity rules expire assumptions so yesterday's context does not silently authorize today's actions.

The result is autonomy that can be proven offline - to operators, to auditors, to third parties through audit bundles containing events, anchors, manifests, and policy proofs.

---

## Repository Structure

The repository contains six integrated components:

**User chat workspace**
Live chat interface for supervised human-entity interaction. Supports session continuity, context-aware responses, and operator-defined policy boundaries.

**Gateway API**
Central API layer routing requests between tenants, entities, and platform integrations. Handles authentication, rate control, approval routing, and event emission.

**Operator control plane**
Internal UI for operator oversight. Surfaces approval queues, entity run state, governance decisions, naturalness analytics, registration artifacts, and platform account management. Operators can inspect, approve, block, or roll back entity actions from a single interface.

**Summary API and UI**
Smaller product-facing surface exposing distilled operational state - recent activity, entity health, approval status - without exposing internal governance detail.

**DAG-backed workflow runtime**
Multi-entity execution engine. entities run as scheduled DAG jobs with defined wake, execute, and sleep cycles. Supports parallel entity operation with verified memory isolation between entities.

**Proof and evidence layer**
Append-only event ledger with integrity linkage. All entity actions emit signed events. High-impact actions require execution receipts and independent verification before commit. Supports offline audit bundle export and replay against pinned policy versions.

---

## Core Concepts

**Governed autonomy**
Actions are gated by executable, versioned policies. Policies produce enforcement decisions and machine-checkable proofs. High-impact actions follow a proposal → approval → execution → verification → commit/rollback cycle. Robustness thresholds block commit if verification evidence is insufficient.

**Governance contracts**
Contractual, scoped rules defining who can approve what, delegation bounds, escalation routes, and timeouts. Contracts are versioned artifacts referenced by all relevant decisions.

**Continuity contracts**
Approvals, assumptions, and verifications carry expiry and revalidation rules. Continuity contracts define validity windows, invalidation triggers, and revalidation workflows. Stale context does not accumulate silently.

**Risk budgeting**
Beyond token counts. Risk is computed from action class and reversibility, environment, dependency fan-out from an impact graph, verifier diversity, and historical regret patterns. The impact graph supports blast radius estimation for incidents and changes.

**Reality gap measurement**
Systems measure divergence between predictions and reality through prediction error, verifier disagreement, anomaly rates, and override rates. Gap scores feed back into governance, tightening autonomy when drift rises.

**Audit bundles**
Exportable packages containing events, anchor proofs, artifact manifests, policy proofs, verification checks, and robustness computations. An offline verifier checks signatures, anchors, manifests, and proofs without network access.

**Pinned replay**
Runs publish a pinset capturing taxonomy versions, policy artifact ids, materializer versions, and tool runner versions. Release compatibility gates replay golden datasets with pinned versions and block drift beyond the declared contract.

---

## Multi-Entity Operation

Hydrogenuine supports parallel autonomous entity operation with verified isolation. Entities share the governance and evidence infrastructure but operate with separate job registries, memory lineages, session continuity, and platform account assignments.

Current operational entities:

- Active across Moltbook and various AI agent dedicated *chans. Research, posting, and engagement DAGs. 24+ hours unattended operation validated.

Entity identity is defined by fingerprint and cannot bleed between entities. Memory isolation is verified before any parallel live run is enabled.

---

## Platform Integrations

Social platform integrations support draft generation, approval routing, live posting, and engagement. Platform credentials are resolved exclusively through the keystore - no plaintext credential files in normal operation paths.

Supported platforms: Moltbook, 4claw, Moltstack, and other dedicated social media.

---

## Operator Safety Model

- **Approval queue** - all entity social writes pass through the approval queue unless an auto-approval policy is active. Operator reviews drafts before publish.
- **Emergency safety gate** - classifier-backed gate blocks posts matching defined risk patterns before they reach the approval queue.
- **Telegram notifications** - queue entry alerts and auto-approval confirmations delivered to operator in real time.
- **Rollback** - governance layer supports rollback of committed actions where the platform permits.
- **Naturalness analytics** - post-run analysis measuring entity voice consistency, register range, and behavioral drift. Feeds operator visibility and governance tuning.

---

## Stack

Python · PostgreSQL · Redis · Next.js · React · Tailwind · Zustand · TanStack Query · Zod · Keycloak SSO

---

## Status

Active development. Core governance, multi-entity runtime, approval layer, and first operational entity are live and validated. Second parallel entity in phased build. Go rewrite planned after Python implementation is fully proven against test suite.

42 tests passing. Live tenant counts: approvals > 148, runs > 923, persona catalog > 215, knowledge documents > 309.

---

## Design Philosophy

Build systems that work when you walk away. No babysitting. No "I thought I fixed that." The operator sets the policy, the system executes, the receipts confirm it happened.

Autonomy without auditability is not autonomy, it is delegation without accountability. Hydrogenuine is built on the principle that the two are not in tension: a well-governed system can be more autonomous, not less, because the operator can trust it further.

