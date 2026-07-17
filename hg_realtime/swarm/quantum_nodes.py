"""Quantum-aware swarm spawn/reduce (additive; classic nodes unchanged)."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Tuple

from hg_quantum.config import (
    get_quantum_config,
    is_enabled,
    is_quantum2_enabled,
    is_quantum2_shadow,
    is_shadow_mode,
)
from hg_quantum.persistence.correlation_store import default_correlation_store
from hg_quantum.entanglement.shell_model import ShellModel
from hg_quantum.entanglement.state_correlator import StateCorrelator
from hg_quantum.entanglement.symmetry_breaker import SymmetryBreaker
from hg_quantum.error_correction.provenance import default_provenance_store
from hg_quantum.error_correction.syndrome_extractor import SyndromeExtractor
from hg_quantum.entanglement.contracts import SymmetryConfig

from .contracts import QuantumSwarmPlan, SwarmPlan
from .nodes import swarm_reduce, swarm_spawn

logger = logging.getLogger(__name__)


def swarm_spawn_quantum(
    *,
    plan: SwarmPlan | QuantumSwarmPlan,
    correlation_id: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Build child payloads with optional symmetry-broken offsets and entanglement metadata.
    Returns (child_payloads, quantum_metadata).
    """
    children = swarm_spawn(plan=plan, correlation_id=correlation_id)
    meta: Dict[str, Any] = {"quantum": {"enabled": False}}
    if not is_enabled("symmetry_breaking") and not getattr(plan, "force_quantum", False):
        return children, meta

    breaker = SymmetryBreaker()
    shell_model = ShellModel()
    shell_assignment = (
        shell_model.assign_shells(plan)
        if plan.tasks and (is_quantum2_enabled("shell_model") or is_quantum2_shadow("shell_model"))
        else None
    )
    symmetry_cfg = getattr(plan, "symmetry_config", None)
    base_fp = getattr(plan, "base_fingerprint", None) or {"cognitive_fingerprint": {}}
    priors_child = children[0] if children else {"learning_priors_enabled": True}
    try:
        from hg_learning.feedback.prior_resolver import learning_priors_from_child

        ctx = learning_priors_from_child(priors_child)
    except ImportError:
        from contextlib import nullcontext

        ctx = nullcontext()
    with ctx:
        task_profile = getattr(plan, "task_profile", None) or {"task_type": "analytical"}
        entity_ids = [
            str((plan.tasks[i] if i < len(plan.tasks) else {}).get("entity_id") or f"child_{i}")
            for i in range(len(children))
        ]
        if symmetry_cfg:
            offsets = breaker.compute_offsets_from_config(symmetry_cfg)
        elif is_quantum2_enabled("shell_model") and shell_assignment is not None:
            offsets = breaker.compute_offsets_with_shells(
                base_fp,
                shell_assignment,
                task_profile,
                entity_order=entity_ids,
            )
        else:
            offsets = breaker.compute_offsets(base_fp, len(children), task_profile)
    stabilizer_meta: Dict[str, Any] = {}
    if is_enabled("dissipative_stabilization") or is_shadow_mode("dissipative_stabilization"):
        try:
            from hg_quantum.entanglement.dissipative_stabilizer import DissipativeStabilizer

            stabilizer = DissipativeStabilizer()
            state_vectors = [dict(offsets[i]) if i < len(offsets) else {} for i in range(len(children))]
            energy_before = stabilizer.system_energy(state_vectors)
            stabilized = stabilizer.stabilize(state_vectors, iterations=20)
            energy_after = stabilizer.system_energy(stabilized)
            stabilizer_meta = {
                "energy_before": energy_before,
                "energy_after": energy_after,
                "applied": is_enabled("dissipative_stabilization"),
                "shadow": is_shadow_mode("dissipative_stabilization") and not is_enabled("dissipative_stabilization"),
            }
            if is_enabled("dissipative_stabilization"):
                offsets = stabilized
            elif is_shadow_mode("dissipative_stabilization"):
                try:
                    from hg_quantum.shadow_telemetry import record_shadow_event

                    record_shadow_event(
                        "dissipative_stabilization",
                        "spawn_stabilize",
                        {
                            "energy_before": energy_before,
                            "energy_after": energy_after,
                            "child_count": len(children),
                        },
                        correlation_id=correlation_id,
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("dissipative_stabilization path failed: %s", exc)
    differentiated = breaker.apply_offsets(base_fp, offsets)
    store = None
    if is_enabled("state_correlation") or is_shadow_mode("state_correlation"):
        try:
            store = default_correlation_store()
        except Exception as exc:
            logger.warning("correlation store unavailable: %s", exc)
    correlator = StateCorrelator(
        fingerprint_id=getattr(plan, "fingerprint_id", "") or "",
        shell_assignment=shell_assignment,
        shell_model=shell_model,
        store=store,
    )
    if store is not None:
        correlator.hydrate_from_store()
    if is_quantum2_shadow("shell_model") and shell_assignment is not None and not is_quantum2_enabled("shell_model"):
        logger.info(
            "quantum2 shell_model shadow: assigned %d shells for correlation_id=%s",
            len(shell_assignment.shells),
            correlation_id,
        )
        try:
            from hg_quantum.shadow_telemetry import record_shadow_event

            naive_offsets = breaker.compute_offsets(base_fp, len(children), task_profile)
            shell_offsets = offsets
            diverged = naive_offsets != shell_offsets
            record_shadow_event(
                "shell_model",
                "offset_compare",
                {
                    "diverged": diverged,
                    "shell_count": len(shell_assignment.shells),
                    "child_count": len(children),
                },
                correlation_id=correlation_id,
            )
        except Exception as exc:
            logger.debug("shell_model shadow telemetry failed: %s", exc)
    pairs = []
    corr_type = "shell_sibling" if is_quantum2_enabled("shell_model") else "swarm_siblings"
    for i in range(len(entity_ids) - 1):
        pairs.append(
            correlator.register_pair(
                entity_ids[i],
                entity_ids[i + 1],
                corr_type,
                fingerprint_id=correlator.fingerprint_id,
            ).to_dict()
        )
    codec_meta: Dict[str, Any] = {}
    if is_quantum2_enabled("fingerprint_codec") or is_quantum2_shadow("fingerprint_codec"):
        try:
            from hg_quantum.shadow_telemetry import record_shadow_event
            from hg_quantum.transport.contracts import ChannelBudget, FingerprintSnapshot
            from hg_quantum.transport.fingerprint_codec import FingerprintBandwidthCodec

            codec = FingerprintBandwidthCodec()
            budget = ChannelBudget(max_bytes=8192)
            for i, child in enumerate(children):
                variant = differentiated[i] if i < len(differentiated) else base_fp
                if not isinstance(variant, dict):
                    continue
                profile = variant if "cognitive_fingerprint" in variant else {"cognitive_fingerprint": variant}
                snap = FingerprintSnapshot(profile=profile)
                encoded = codec.encode(snap, budget)
                fidelity = codec.fidelity_report(encoded)
                if is_quantum2_shadow("fingerprint_codec") and not is_quantum2_enabled("fingerprint_codec"):
                    record_shadow_event(
                        "fingerprint_codec",
                        "encode_shadow",
                        {
                            "diverged": fidelity.descriptive_divergence > 0,
                            "divergence": fidelity.descriptive_divergence,
                            "byte_size": encoded.byte_size,
                            "mode": encoded.descriptive_mode,
                            "entity_id": entity_ids[i],
                        },
                        correlation_id=correlation_id,
                    )
                elif is_quantum2_enabled("fingerprint_codec"):
                    child.setdefault("quantum_codec", encoded.to_dict())
            codec_meta = {"codec_active": is_quantum2_enabled("fingerprint_codec")}
        except Exception as exc:
            logger.debug("fingerprint_codec path failed: %s", exc)
    for i, child in enumerate(children):
        shell = shell_assignment.entity_shell.get(entity_ids[i], "") if shell_assignment else ""
        child["quantum"] = {
            "entity_id": entity_ids[i],
            "shell": shell,
            "trait_offsets": offsets[i] if i < len(offsets) else {},
            "fingerprint_variant": differentiated[i] if i < len(differentiated) else base_fp,
        }
    meta = {
        "quantum": {
            "enabled": True,
            "shadow": is_shadow_mode("symmetry_breaking"),
            "entangled_pairs": pairs,
            "child_entity_ids": entity_ids,
            **codec_meta,
            **({"dissipative_stabilization": stabilizer_meta} if stabilizer_meta else {}),
        }
    }
    return children, meta


def swarm_reduce_quantum(
    *,
    child_outputs: List[Dict[str, Any]],
    swarm_run_id: str = "",
    plan: SwarmPlan | QuantumSwarmPlan | None = None,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Aggregate child outputs with optional LDPC verification.
    Shadow mode logs disagreements vs classic reduce without changing outcome.
    """
    classic_summary, classic_artifacts, classic_warnings = swarm_reduce(child_outputs=child_outputs)
    cfg = get_quantum_config()
    ldpc_on = is_enabled("ldpc_verification") or bool(getattr(plan, "force_quantum", False) if plan else False)
    if not ldpc_on:
        return classic_summary, classic_artifacts, classic_warnings

    started = time.monotonic()
    shadow = is_shadow_mode("ldpc_verification")
    extractor = SyndromeExtractor()
    graph = getattr(plan, "verification_graph", None) if plan else None
    if graph is None:
        verification = extractor.build_verification_graph(
            child_outputs,
            graph_id=f"vg_{swarm_run_id or uuid.uuid4().hex[:8]}",
            swarm_plan=plan,
        )
    else:
        verification = graph
    syndromes = extractor.extract_syndromes(child_outputs, verification, swarm_run_id=swarm_run_id)
    risk_skew = getattr(plan, "risk_skew", None) if plan else None
    actions = extractor.decode_correction(
        syndromes,
        graph=verification,
        risk_skew=risk_skew if isinstance(risk_skew, dict) else None,
    )
    elapsed_ms = (time.monotonic() - started) * 1000.0
    if elapsed_ms > float(cfg.get("latency_budget_ms", 500)) and cfg.get("fallback_on_error", True):
        logger.warning("quantum reduce latency %.1fms > budget; falling back to classic", elapsed_ms)
        return classic_summary, classic_artifacts, classic_warnings + ["quantum_latency_fallback"]

    quantum_summary = f"LDPC-verified reduce: {len(child_outputs)} outputs, {len(syndromes)} syndromes"
    quantum_artifacts: Dict[str, Any] = {
        **classic_artifacts,
        "verification_graph": verification.to_dict(),
        "syndrome_count": len(syndromes),
        "syndromes": [s.to_dict() for s in syndromes],
        "correction_actions": [a.to_dict() for a in actions],
        "quantum_elapsed_ms": elapsed_ms,
    }
    quantum_warnings = list(classic_warnings)
    if syndromes:
        quantum_warnings.append(f"detected {len(syndromes)} output syndromes")

    try:
        store = default_provenance_store()
        store.append(
            swarm_run_id=swarm_run_id or "unknown",
            syndromes=syndromes,
            actions=actions,
            input_fingerprints=[str(o.get("run_id", i)) for i, o in enumerate(child_outputs)],
        )
    except Exception as exc:
        logger.warning("provenance append failed: %s", exc)

    if shadow:
        disagrees = quantum_summary != classic_summary or len(syndromes) > 0
        if disagrees:
            logger.info(
                "quantum shadow reduce disagreement swarm=%s syndromes=%d classic=%r quantum=%r",
                swarm_run_id,
                len(syndromes),
                classic_summary,
                quantum_summary,
            )
            try:
                from hg_quantum.shadow_telemetry import record_shadow_event

                record_shadow_event(
                    "ldpc_verification",
                    "reduce_compare",
                    {
                        "diverged": disagrees,
                        "syndrome_count": len(syndromes),
                        "classic_summary": classic_summary,
                        "quantum_summary": quantum_summary,
                    },
                    correlation_id=swarm_run_id,
                )
            except Exception:
                pass
        return classic_summary, {**classic_artifacts, "quantum_shadow": quantum_artifacts}, quantum_warnings

    if actions and not shadow:
        quantum_artifacts["applied_correction"] = actions[0].to_dict()
    return quantum_summary, quantum_artifacts, quantum_warnings


def reduce_for_plan(
    *,
    plan: SwarmPlan | QuantumSwarmPlan,
    child_outputs: List[Dict[str, Any]],
    swarm_run_id: str,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Dispatch classic or quantum reduce based on flags and plan."""
    if is_enabled("ldpc_verification") or getattr(plan, "force_quantum", False):
        return swarm_reduce_quantum(
            child_outputs=child_outputs,
            swarm_run_id=swarm_run_id,
            plan=plan,
        )
    return swarm_reduce(child_outputs=child_outputs)
