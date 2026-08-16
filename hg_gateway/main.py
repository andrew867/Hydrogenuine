"""
HG Chat Gateway FastAPI app.

Mount at /v1 for chats, messages, agents, approvals, SSE stream, and WebSocket.
"""

import os

try:
    from hg_cli.config import apply_config_to_environment

    # Launchers set this explicitly. Do not silently discover a config from the
    # process working directory: an embedded gateway, test runner, or legacy
    # deployment may share that directory without opting into Community mode.
    _community_config_path = os.environ.get("HG_CONFIG_PATH", "").strip()
    if _community_config_path:
        apply_config_to_environment()
except Exception:
    # A missing or invalid Community config is reported by ``hg doctor``. Keep
    # legacy deployments importable so their explicit environment still works.
    pass

# Apply env.vars from hg.json (HG_CONFIG) so OpenVINO, LLM keys available when gateway runs standalone
try:
    from hg_core.setup_data import apply_hg_env_to_process
    apply_hg_env_to_process()
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hg_gateway.auth import (
    runtime_auth_diagnostics,
    runtime_safety_diagnostics,
    validate_runtime_auth_config,
    validate_runtime_safety_config,
)
from hg_gateway.storage_config import gateway_storage_diagnostics, validate_gateway_storage_config
from hg_gateway.routes import router as v1_router
from hg_gateway.routes_ui_brand import router as ui_brand_router
from hg_gateway.routes_files import router as files_router
from hg_gateway.routes_documents import router as documents_router
from hg_gateway.routes_analytics import router as analytics_router
from hg_gateway.routes_schedule import router as schedule_router
from hg_gateway.routes_steering import router as steering_router
from hg_gateway.routes_utility import router as utility_router
from hg_gateway.routes_recognition import router as recognition_router
from hg_gateway.stream_routes import router as stream_router
from hg_gateway.routes_notifications import router as notifications_router
from hg_gateway.admin_proofs import router as admin_proofs_router
from hg_gateway.routes_replay import router as replay_router
from hg_gateway.auth_routes import router as auth_router
from hg_gateway.operator_decision_routes import router as operator_decision_router
from hg_gateway.workbench_routes import router as workbench_router
from hg_gateway.routes_scim import router as scim_router
from hg_gateway.middleware import RequestIDMiddleware
from hg_gateway.otel_runtime import configure_otel, runtime_diagnostics as otel_runtime_diagnostics, shutdown_otel
from hg_gateway.llm_defaults import is_safe_local_only
from hg_gateway import tools as gateway_tools
from hg_realtime.worker import runtime_bus_mode

validate_runtime_auth_config()
validate_runtime_safety_config()
validate_gateway_storage_config()
configure_otel()

try:
    from hg_core.gate.service import ensure_demo_backup_stub

    _demo_backup_dir = ensure_demo_backup_stub()
    if _demo_backup_dir:
        print(f"[gateway] created demo backup marker at {_demo_backup_dir}")
except Exception:
    pass

app = FastAPI(title="HG Chat Gateway", version="0.1")


def _cors_origins() -> list[str]:
    raw = (os.environ.get("HG_CORS_ALLOWED_ORIGINS") or "").strip()
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(v1_router, prefix="/v1", tags=["v1"])
app.include_router(ui_brand_router, prefix="/v1", tags=["ui"])
app.include_router(files_router, prefix="/v1", tags=["files"])
app.include_router(documents_router, prefix="/v1", tags=["documents"])
app.include_router(analytics_router, prefix="/v1", tags=["analytics"])
app.include_router(schedule_router, prefix="/v1", tags=["schedule"])
app.include_router(steering_router, prefix="/v1", tags=["steering"])
app.include_router(utility_router, prefix="/v1", tags=["utility"])
app.include_router(recognition_router, prefix="/v1", tags=["recognition"])
app.include_router(stream_router, prefix="/v1", tags=["stream"])
app.include_router(notifications_router, prefix="/v1", tags=["notifications"])
app.include_router(admin_proofs_router, prefix="/v1")
app.include_router(replay_router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")
app.include_router(operator_decision_router, prefix="/v1", tags=["operator-decisions"])
app.include_router(workbench_router, prefix="/v1", tags=["workbench"])
app.include_router(scim_router)

print(
    "[gateway] runtime_auth=%s runtime_safety=%s storage=%s tool_runtime=%s realtime_bus_mode=%s otel=%s safe_local_only=%s"
    % (
        runtime_auth_diagnostics(),
        runtime_safety_diagnostics(),
        gateway_storage_diagnostics(),
        gateway_tools.get_runtime_diagnostics(),
        runtime_bus_mode(),
        otel_runtime_diagnostics(),
        is_safe_local_only(),
    )
)


@app.get("/healthz")
def healthz():
    auth_mode = (os.environ.get("HG_GATEWAY_AUTH_MODE") or "api-key").strip().lower()
    return {
        "ok": True,
        "edition": "community",
        "auth_mode": auth_mode,
        "provider_mode": (os.environ.get("HG_DEFAULT_PROVIDER") or "stub").strip().lower(),
        "storage": gateway_storage_diagnostics(),
    }


@app.on_event("shutdown")
def _shutdown_runtime() -> None:
    shutdown_otel()
