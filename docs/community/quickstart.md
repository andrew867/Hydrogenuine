# Community quickstart

Run `.\start.ps1` on Windows or `./start.sh` on Linux/macOS, then open `http://127.0.0.1:4173`.

The first launcher run performs these steps:

1. Creates `.venv`.
2. Installs the package and development test dependency.
3. Runs no-key demo initialization if `.hg_community/config.json` does not exist.
4. Starts a loopback-only gateway on port 8000.
5. Starts the static Community UI on port 4173.
6. Stores chat sessions in `.hg_community/gateway.sqlite3`.

No model-provider key, LM Studio process, cloud service, or private Hydrogenuine component is required.

Verify the installation:

```bash
hg doctor --self-test
hg demo
hg chat new --title "First chat"
hg chat list
```

On source clones, use `.\.venv\Scripts\hg.exe` on Windows or `./.venv/bin/hg` on Linux/macOS when the virtual environment is not activated.

Configure LM Studio:

```bash
hg init --force --mode local --provider lm-studio --base-url http://127.0.0.1:1234/v1 --model local-model --non-interactive
hg doctor
```

Restart Hydrogenuine after changing modes. See `CONFIGURATION.md` and `TROUBLESHOOTING.md` at the repository root.
