# OSS first-run UX test report

Date: 2026-08-16

## Automated test result

Command:

```text
python -m pytest tests/test_oss_first_run_cli.py tests/test_oss_first_run_gateway.py tests/test_community_backend_acceptance.py tests/test_community_redteam.py tests/test_public_packaging_docs.py tests/test_gateway_runtime_config.py tests/test_gateway_runtime_safety.py tests/test_gateway_llm_fallback.py tests/test_llm_defaults.py -q
```

Result before final gate: `32 passed`.

Covered behavior:

- clean demo initialization with no gateway or provider keys
- safe config contents and redacted display
- mocked LM Studio/OpenAI-compatible endpoint validation
- precise missing selected cloud-key remediation
- loopback no-key gateway access
- stale browser token regression
- precise local transport credential error in explicit key mode
- configured cloud-provider fallback remains optional and nonfatal
- SQLite multi-chat persistence across store recreation
- CLI chat create, list, active selection, and resume
- Community backend acceptance flow
- public documentation and packaging checks
- gateway runtime configuration and safety regression coverage
- Community red-team checks

## Manual clean-install smoke

The branch was exercised from a fresh clone with provider key variables removed.

- `start.ps1` created a safe demo configuration and launched successfully.
- Public health reported `auth_mode=local-no-key`, `provider_mode=stub`, and SQLite storage.
- A request without a key succeeded.
- A request carrying a stale saved browser token also succeeded because local no-key mode ignores it.
- `hg doctor --self-test` passed and created two deterministic receipts without network access.
- Two chats were created, the documented launcher was stopped and restarted, both chats remained listed, and the first chat resumed successfully.
- `tools/verify_no_bytecode_only_export.py .` reported no bytecode-only directories.

## Warnings

The focused run emitted existing framework deprecation warnings for the Starlette/FastAPI test client and FastAPI `on_event`. They did not fail the scoped tests. They are not presented as resolved by this tranche.

## Final gate

`GREEN_OSS_FIRST_RUN_UX_READY` passed with the expanded 32-test selection and all static readiness checks.
