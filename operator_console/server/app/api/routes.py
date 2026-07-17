from fastapi import APIRouter

from .activity import router as activity
from .advanced_models import router as advanced_models_router
from .agent0 import router as agent0_router
from .analytics import router as analytics
from .approvals_entity import router as approvals_entity_router
from .artifact_registry import router as artifact_registry_router
from .artifacts import router as artifacts
from .browser_sessions import router as browser_sessions_router
from .checkpoints import router as checkpoints
from .config_api import router as config_router
from .consent import router as consent_router
from .content_registry import router as content_registry_router
from .delegation import router as delegation
from .entities import router as entities
from .evals import router as evals_router
from .events import router as events
from .executable_registry import router as executable_registry_router
from .fault import router as fault
from .governance import router as governance_router
from .graphs import router as graphs
from .knowledge import router as knowledge
from .learning_panels import router as learning_panels_router
from .mediator_panels import router as mediator_panels_router
from .operator_actions import router as operator_actions
from .ownership import router as ownership
from .ownership_controls import router as ownership_controls
from .physical_agents import router as physical_agents_router
from .process_audit import router as process_audit
from .product_v1 import router as product_v1_router
from .proof_reconstruction import router as proof_reconstruction_router
from .quantum2_activation import router as quantum2_activation_router
from .quantum2_panels import router as quantum2_panels_router
from .recovery import router as recovery_router
from .reflections import router as reflections_router
from .reliability import router as reliability
from .repr_interp import router as repr_interp
from .retention import router as retention
from .runs import router as runs
from .search import router as search_router
from .sla import router as sla
from .snapshots import router as snapshots
from .social_entity import router as social_entity_router
from .source_blob_registry import router as source_blob_registry_router
from .status import router as status
from .steering import router as steering
from .task_registry import router as task_registry_router
from .templates import router as templates
from .tools_entity import router as tools_entity_router
from .trust_metrics import router as trust_metrics_router
from .user_recognition import router as user_recognition_router
from .workflows import router as workflows

api_router = APIRouter()
api_router.include_router(graphs, prefix="/graphs", tags=["graphs"])
api_router.include_router(status, prefix="/status", tags=["status"])
api_router.include_router(workflows, prefix="/workflows", tags=["workflows"])
api_router.include_router(fault, prefix="/fault", tags=["fault"])
api_router.include_router(retention, prefix="/retention", tags=["retention"])
api_router.include_router(trust_metrics_router, prefix="/proofs", tags=["proofs-trust"])
api_router.include_router(recovery_router, prefix="/recovery", tags=["recovery"])
api_router.include_router(consent_router, prefix="/consent", tags=["consent"])
api_router.include_router(user_recognition_router, prefix="/user-recognition", tags=["user-recognition"])
api_router.include_router(proof_reconstruction_router, prefix="/proof-reconstruction", tags=["proof-reconstruction"])
api_router.include_router(advanced_models_router, prefix="/advanced-models", tags=["advanced-models"])
api_router.include_router(learning_panels_router, prefix="/learning", tags=["learning"])
api_router.include_router(operator_actions, prefix="/operator", tags=["operator"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(agent0_router, prefix="/agent0", tags=["agent0"])
api_router.include_router(sla, prefix="/sla", tags=["sla"])
api_router.include_router(reliability, prefix="/reliability", tags=["reliability"])
api_router.include_router(ownership_controls, prefix="/ownership", tags=["ownership"])
api_router.include_router(steering, prefix="/steering", tags=["steering"])
api_router.include_router(events, prefix="/events", tags=["events"])
api_router.include_router(runs, prefix="/runs", tags=["runs"])
api_router.include_router(artifacts, prefix="/runs", tags=["artifacts"])
api_router.include_router(delegation, prefix="/runs", tags=["delegation"])
api_router.include_router(snapshots, prefix="/runs", tags=["snapshots"])
api_router.include_router(checkpoints, prefix="/runs", tags=["checkpoints"])
api_router.include_router(ownership, prefix="/runs", tags=["ownership"])
api_router.include_router(analytics, prefix="/runs", tags=["analytics"])
api_router.include_router(entities, prefix="/entities", tags=["entities"])
api_router.include_router(knowledge, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(activity, prefix="/activity", tags=["activity"])
api_router.include_router(templates, prefix="/templates", tags=["templates"])
api_router.include_router(repr_interp, prefix="/repr-interp", tags=["repr-interp"])
api_router.include_router(process_audit, tags=["process-audit"])
api_router.include_router(evals_router, prefix="/evals", tags=["evals"])
api_router.include_router(approvals_entity_router, prefix="/approvals-entity", tags=["approvals-entity"])
api_router.include_router(tools_entity_router, prefix="/tools", tags=["tools-entity"])
api_router.include_router(browser_sessions_router, prefix="/browser-sessions", tags=["browser-sessions"])
api_router.include_router(social_entity_router, prefix="/social-entity", tags=["social-entity"])
api_router.include_router(governance_router, prefix="/governance", tags=["governance"])
api_router.include_router(content_registry_router, prefix="/content", tags=["content"])
api_router.include_router(artifact_registry_router, prefix="/artifact-registry", tags=["artifact-registry"])
api_router.include_router(reflections, tags=["reflections"])
api_router.include_router(source_blob_registry, prefix="/source-registry", tags=["source-registry"])
api_router.include_router(executable_registry, prefix="/executable-registry", tags=["executable-registry"])
api_router.include_router(task_registry, prefix="/task-registry", tags=["task-registry"])
api_router.include_router(product_v1_router, prefix="/product", tags=["product"])
