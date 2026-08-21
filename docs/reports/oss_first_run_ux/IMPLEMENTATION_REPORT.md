# OSS first-run UX implementation report

## Implementation summary

The fix is implemented on a private local branch based on the current public release commit. Nothing was pushed or published.

## Command surface

- `hg init`
- `hg doctor [--self-test]`
- `hg config show --redacted`
- `hg demo`
- `hg chat new`
- `hg chat list`
- `hg chat resume`

The compatibility command `hg-setup` now opens the Community first-run wizard instead of the legacy broad API-key setup.

## Setup modes

- Demo: deterministic, offline, and no-key.
- Local: LM Studio or generic OpenAI-compatible endpoint, validated through `GET /models`, with no cloud key.
- Cloud: selected provider plus an environment-variable reference. The secret value is not written.
- Private: explicit boundary marker. Community doctor reports that private components are absent.

## Gateway and UI behavior

- Native demo and local modes use loopback-only `local-no-key` gateway access.
- The gateway refuses no-key mode outside demo/development runtime labels.
- Key mode errors identify the credential as a local HTTP transport credential, not a model-provider key.
- The UI reads public health before protected routes and ignores stale browser tokens in no-key mode.
- The UI exposes a Reset saved connection action and no longer reports every authentication mismatch as API offline.
- The selected runtime provider, model, and base URL are included in chat turns.
- Unselected or missing providers are optional-unavailable; demo chat remains usable.
- Configured cloud providers remain optional fallback candidates; absent provider keys do not block startup.
- Gateway configuration is applied only when a launcher explicitly supplies `HG_CONFIG_PATH`, preventing a working-directory config from changing embedded, legacy, or test runtimes unexpectedly.

## Multi-chat behavior

- Native and Docker launchers now select SQLite.
- New chat, list, branch selection, CLI active-chat selection, resume, and one-turn resume are implemented.
- Chat history survives gateway store recreation in the integration test.

## Additional defect fixed

Switching Community acceptance tests to SQLite exposed an existing archive route mismatch. The route called `chat_patch(..., archived=True)` even though the SQLite store implements `chat_set_archived`. The route now uses the supported store method.

## Files and boundaries

All new configuration defaults to an ignored Community data directory or the user's Hydrogenuine configuration directory. No secrets, private endpoints, private proof bundles, or public remote changes were introduced.
