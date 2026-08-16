# Hydrogenuine Community configuration

Run `hg init` for an interactive setup or pass a mode for repeatable setup.

## Where configuration lives

Source-clone launchers use `.hg_community/config.json`. A standalone installed `hg` command defaults to `~/.hydrogenuine/config.json`. Override the path with `HG_CONFIG_PATH` or `--config`.

The file contains:

- selected mode
- local data directory
- local API URL
- provider identifier, model, and endpoint
- provider key environment-variable name when cloud mode is selected
- last active CLI chat ID

It does not contain secret values. `hg config show --redacted` redacts any unexpected secret-like extension fields as a second safety layer.

## Demo mode

```bash
hg init --force --mode demo --non-interactive
```

Behavior:

- deterministic stub provider
- no network
- no model-provider key
- loopback-only no-key gateway access
- persistent local SQLite chat store when started with the platform launcher

## Local OpenAI-compatible mode

LM Studio example:

```bash
hg init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model local-model --non-interactive
```

Generic endpoint example:

```bash
hg init --force --mode local --provider openai-compatible --base-url http://127.0.0.1:11434/v1 --model local-model --non-interactive
```

The wizard calls `GET /models` and refuses to claim the endpoint is ready when it cannot connect. Use `--skip-validation` only to save future configuration. `hg doctor` then reports the provider as unavailable, not as a fatal failure of the Community core.

Local model mode requires no cloud key. Restart the gateway after changing mode.

## Cloud mode

```bash
hg init --force --mode cloud --provider openai --model gpt-4.1-mini --key-env OPENAI_API_KEY --non-interactive
```

Supported configuration identifiers are `openai`, `anthropic`, `google`, and `xai`. Set the selected key only in the process environment:

```powershell
$env:OPENAI_API_KEY = "your value"
```

```bash
export OPENAI_API_KEY="your value"
```

The value is not written by Hydrogenuine. When a selected cloud credential is absent, `hg doctor` names the missing environment variable and suggests returning to demo mode. Other unselected providers remain optional and do not fail startup.

## Private/commercial mode

```bash
hg init --force --mode private --non-interactive
```

This records the requested boundary only. The Community repository does not include the private/commercial Hydrogenuine stack, private endpoints, managed tenancy, private proof vaults, policy packs, or proprietary connectors. `hg doctor` reports that boundary as needing attention rather than implying the OSS core is broken.

## Gateway access modes

`local-no-key` is only accepted for loopback clients in demo-like runtime environments. The gateway refuses this mode outside demo/development runtime labels.

`api-key` protects the local HTTP gateway with `HG_GATEWAY_API_KEY`. It is a transport credential and is unrelated to model-provider credentials.

Do not expose the Community gateway beyond the local machine while using no-key mode.

## Data storage

Native startup defaults to:

```text
.hg_community/config.json
.hg_community/gateway.sqlite3
.hg_community/community.json
```

The directory is excluded from git. Change it with `HG_COMMUNITY_DATA_DIR`.
