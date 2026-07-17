# Backend (FastAPI)

Serves the Operator Console API (DAG runs, artifacts, checkpoints, ownership, analytics; **entities**, **knowledge**, **config**, **activity**). Requires `PYTHONPATH` set to workspace root for `hg_core`; optional `hg_knowledge` and `hg_lib` for knowledge/config/entities (graceful fallback if missing).

Windows:
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn pydantic python-multipart

Run:
set HG_API_KEY=changeme
set HG_RUNS_ROOT=.\.hg_runs
set HG_DB_PATH=.\hg_console.db
set HG_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080
set PYTHONPATH=<workspace_root>

uvicorn app.main:app --reload --port 8080

If HG_API_KEY is not set, the server will fall back to the gateway token
from %USERPROFILE%\.hg\hg.json (gateway.auth.token).
