# Install Hydrogenuine Community

Hydrogenuine Community is an early public pre-alpha. The supported first-run path is a source clone plus the platform launcher.

## Requirements

- Python 3.10 or newer
- Git
- About 2 GB of free space for the virtual environment and dependencies
- Optional: Docker Desktop or a compatible Docker installation
- Optional: LM Studio or another OpenAI-compatible model server

No model-provider key is required for installation or demo mode.

## Windows

```powershell
git clone https://github.com/andrew867/Hydrogenuine.git
cd Hydrogenuine
.\start.ps1
```

The script creates `.venv`, installs Hydrogenuine in editable mode, initializes no-key demo mode when no configuration exists, and starts two hidden local processes. Open `http://127.0.0.1:4173`.

Validate it:

```powershell
.\.venv\Scripts\hg.exe doctor --self-test
.\.venv\Scripts\hg.exe chat new --title "First chat"
.\.venv\Scripts\hg.exe chat list
```

Stop it:

```powershell
.\stop.ps1
```

## Linux or macOS

```bash
git clone https://github.com/andrew867/Hydrogenuine.git
cd Hydrogenuine
./start.sh
```

Validate it:

```bash
./.venv/bin/hg doctor --self-test
./.venv/bin/hg chat new --title "First chat"
./.venv/bin/hg chat list
```

Stop it with `./stop.sh`.

## Manual package install

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
hg init --mode demo --non-interactive
hg doctor --self-test
```

The exact activation syntax for `.venv` depends on your shell. You can always call the `hg` executable by its full path as shown above.

## Docker

```bash
docker compose up --build
```

Open `http://127.0.0.1:4173`. The deterministic demo does not require a provider key. Docker uses a built-in local gateway transport token so the browser UI and API agree without manual configuration.

## Upgrading an older local clone

Older browsers may contain `hg_api_key` in local storage. Native no-key mode ignores it. If an older custom gateway configuration still rejects the browser, open Data Settings and select Reset saved connection, then run `hg doctor`.

Existing `.env` files are not overwritten. Compare yours with `.env.example`, remove obsolete demo-key settings if using native no-key mode, and restart.
