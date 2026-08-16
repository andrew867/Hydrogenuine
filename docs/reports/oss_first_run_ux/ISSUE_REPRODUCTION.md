# OSS first-run issue reproduction

Date: 2026-08-16

## Released baseline

- Repository: `andrew867/Hydrogenuine`
- Fresh clone branch: `main`
- Fresh clone commit: `bb78773651a3612ab39578eb71eed91b5b83d47e`
- Release tag: `v0.1.1`
- Platform used for reproduction: Windows PowerShell, Python 3.13
- Provider keys removed from the reproduction process: OpenAI, Anthropic, Google, xAI, and Hydrogenuine gateway key

## Documented command result

Running `.\start.ps1` from a new clone completed installation and started the API and UI. With the shipped default `oss-demo-key`, `GET /v1/chats` returned 200. The fully clean default path did not itself produce the reported failure.

## Exact reported failure path

The Community UI loads its gateway value from browser local storage:

```text
localStorage["hg_api_key"] or "oss-demo-key"
```

When that saved value differs from `HG_GATEWAY_API_KEY`, the released gateway returns:

```text
HTTP 401
{"detail":"Invalid API key"}
```

The released UI catches the exception, discards its detail during the initial refresh, and labels the whole API `offline`. The error is therefore reproducible with a stale browser value, an older `.env`, a custom gateway value, or a Docker/native configuration mismatch.

## Root causes

1. A local gateway transport credential was presented to users as an unspecified API key, making it indistinguishable from a model-provider key.
2. Native local demo required a shared token even though the gateway was bound to loopback.
3. The UI persisted an old token but provided no direct reset or precise initial-load remediation.
4. The published `hg-setup` entry point opened a broad private-oriented wizard that foregrounded multiple cloud and platform keys.
5. The README documented `HG_MODEL_PROVIDER`, while runtime default selection used different variables.
6. The UI always posted chat messages with `provider: "stub"`, so advertised provider settings did not select the configured provider.
7. Native startup selected the in-memory gateway store, so multi-chat history did not survive restart.
8. Public docs did not explain CLI multi-chat creation, list, resume, local provider validation, or the OSS/private boundary in one coherent path.

## Claim boundary

This reproduction proves the released local authentication mismatch and UX behavior. It does not identify the reporter's exact browser state or environment because that machine was not available for inspection.
