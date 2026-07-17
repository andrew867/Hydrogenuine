from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from hg_core.setup_data import apply_hg_env_to_process

    apply_hg_env_to_process()
except Exception:
    pass

from .api.product_v1 import router as product_v1_router
from .api.routes import api_router
from .core.config import settings, validate_operator_runtime_config
from hg_gateway.routes_analytics import router as analytics_router

validate_operator_runtime_config()

app = FastAPI(title="Hydrogenuine Community Operator API", version="0.2")


def _log_api_key_source() -> None:
    source = getattr(settings, "api_key_source", "unknown")
    strict = getattr(settings, "strict_auth_required", False)
    env_label = getattr(settings, "runtime_env", "unknown")
    safe_local_only = getattr(settings, "safe_local_only", False)
    print(f"[operator_api] api_key_source={source} strict_auth_required={strict} env={env_label} safe_local_only={safe_local_only}")


_log_api_key_source()

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")
app.include_router(product_v1_router, prefix="/api/product/v1", tags=["product-v1"])

try:
    from hg_gateway.admin_proofs import router as admin_proofs_router
    from hg_gateway.auth_routes import router as auth_router
    from hg_gateway.routes import router as chat_router
    from hg_gateway.routes_documents import router as documents_router
    from hg_gateway.routes_files import router as files_router
    from hg_gateway.routes_replay import router as replay_router
    from hg_gateway.routes_ui_brand import router as ui_brand_router
    from hg_gateway.stream_routes import router as stream_router

    app.include_router(chat_router, prefix="/v1", tags=["chat"])
    app.include_router(ui_brand_router, prefix="/v1", tags=["ui-brand"])
    app.include_router(files_router, prefix="/v1", tags=["files"])
    app.include_router(documents_router, prefix="/v1", tags=["documents"])
    app.include_router(analytics_router, prefix="/v1", tags=["analytics"])
    app.include_router(stream_router, prefix="/v1", tags=["chat-stream"])
    app.include_router(replay_router, prefix="/v1", tags=["admin-replay"])
    app.include_router(admin_proofs_router, prefix="/v1", tags=["admin-proofs"])
    app.include_router(auth_router, prefix="/v1", tags=["auth"])
except ImportError:
    pass


@app.get("/healthz")
def healthz():
    return {"ok": True}
