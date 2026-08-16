# Troubleshooting Hydrogenuine Community

## The UI says local access needs attention

This means the gateway answered, but an older browser-saved local transport token does not match the gateway's selected access mode. It does not mean an OpenAI, Anthropic, Google, xAI, or LM Studio key is invalid.

1. Run `hg doctor`.
2. In the UI, open Data Settings and select Reset saved connection.
3. Restart with `./stop.sh` and `./start.sh`, or the PowerShell equivalents.
4. Confirm `http://127.0.0.1:8000/healthz` reports `"auth_mode":"local-no-key"` for native demo mode.

## The UI says API offline

Check that both services are running and that ports 8000 and 4173 are available. Run `hg doctor --self-test`. The self-test is in-process and can distinguish a working installation from a stopped web service.

## No cloud key is configured

That is expected in demo and local-model modes. Unselected providers are optional. They appear as unavailable and do not make the Community core fail.

If cloud mode is selected, `hg doctor` prints the exact required environment variable. Set it in the shell that starts Hydrogenuine, or return to demo mode:

```bash
hg init --force --mode demo --non-interactive
```

## LM Studio is unavailable

1. Start LM Studio's local server.
2. Load a model.
3. Confirm its OpenAI-compatible port, commonly 1234.
4. Run `hg init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model YOUR_MODEL --non-interactive`.
5. Run `hg doctor`.
6. Restart Hydrogenuine.

Hydrogenuine remains usable in demo mode while LM Studio is stopped.

## Chats disappear after restart

Current native and Docker launchers use SQLite. Run `hg config show --redacted` and confirm your data directory. Check `.env` for an older `HG_GATEWAY_STORE=memory` override. Replace it with `HG_GATEWAY_STORE=sqlite` and set `HG_GATEWAY_DB_PATH` inside the Community data directory.

## `hg` is not found

Use the virtual-environment executable directly:

- Windows: `.\.venv\Scripts\hg.exe`
- Linux or macOS: `./.venv/bin/hg`

If it is missing, rerun the platform launcher or install with `python -m pip install -e ".[dev]"`.

## A private/commercial feature is missing

The public repository intentionally excludes managed tenancy, enterprise SSO, private proof vaults, private policy packs, customer data, proprietary connectors, and private operator infrastructure. Use `hg init --mode demo`, `local`, or `cloud` for the OSS core. The private mode is a boundary marker, not a downloader.

## Report a defect

Include:

- operating system and Python version
- the redacted output of `hg config show --redacted`
- the output of `hg doctor`
- the command that failed
- whether the failure occurs in demo, local, cloud, or private mode

Never include provider key values, `.env` contents containing secrets, private endpoints, or private proof bundles.
