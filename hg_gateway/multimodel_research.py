"""Bounded multi-model research orchestration for Hydrogenuine Community.

Two or more analyst models receive the same source pack independently. A
different synthesis model receives the source pack plus the completed analyst
outputs and produces one bounded conclusion. Secret values are resolved only
by the provider adapter and are never included in the returned run record.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from hg_llm import ProviderRegistry, get_default_registry
from hg_core.secrets.redact import redact_text


SCHEMA = "hydrogenuine-multimodel-research-v1"
DEFAULT_PACK_ID = "oss-first-run-v1"
DEFAULT_ANALYST_MODELS = ["qwen2.5-1.5b-instruct", "smollm2-1.7b"]
DEFAULT_SYNTHESIS_MODEL = "qwen3-4b-2507"
DEFAULT_LOCAL_BASE_URL = "http://127.0.0.1:1234/v1"
MAX_SOURCE_BYTES = 120_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def run_hash_payload(run: Dict[str, Any]) -> Dict[str, Any]:
    """Return the stable, receipt-independent payload bound by ``run_sha256``."""
    return {
        key: value
        for key, value in run.items()
        if key not in {"run_sha256", "receipt_ids", "updated_at"}
    }


def _safe_error(error: Exception) -> str:
    return redact_text(str(error))[0][:500]


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_source_pack(pack_id: str = DEFAULT_PACK_ID, *, root: Optional[Path] = None) -> Dict[str, Any]:
    if pack_id != DEFAULT_PACK_ID:
        raise ValueError(f"Unsupported source pack: {pack_id}")
    base = (root or repository_root()).resolve()
    manifest_path = base / "examples" / "research" / "oss_first_run_source_pack.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources: List[Dict[str, Any]] = []
    total_bytes = 0
    for index, item in enumerate(manifest.get("sources") or [], 1):
        relative = Path(str(item["path"]))
        source_path = (base / relative).resolve()
        try:
            source_path.relative_to(base)
        except ValueError as exc:
            raise ValueError(f"Source path escapes repository root: {relative}") from exc
        content = source_path.read_text(encoding="utf-8")
        byte_count = len(content.encode("utf-8"))
        total_bytes += byte_count
        if total_bytes > MAX_SOURCE_BYTES:
            raise ValueError(f"Source pack exceeds {MAX_SOURCE_BYTES} bytes")
        sources.append(
            {
                "source_id": str(item.get("source_id") or f"S{index}"),
                "title": str(item.get("title") or relative.name),
                "path": relative.as_posix(),
                "claim_boundary": str(item.get("claim_boundary") or "repository evidence only"),
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "bytes": byte_count,
                "content": content,
            }
        )
    if len(sources) < 2:
        raise ValueError("Multi-model research requires at least two source records")
    pack_for_hash = {
        "schema": manifest.get("schema"),
        "pack_id": pack_id,
        "question": manifest.get("question"),
        "sources": sources,
    }
    return {
        "schema": str(manifest.get("schema") or "hydrogenuine-source-pack-v1"),
        "pack_id": pack_id,
        "question": str(manifest.get("question") or "").strip(),
        "sources": sources,
        "source_pack_sha256": sha256_value(pack_for_hash),
        "total_bytes": total_bytes,
    }


def public_source_records(source_pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{key: value for key, value in source.items() if key != "content"} for source in source_pack["sources"]]


def _source_text(source_pack: Dict[str, Any]) -> str:
    blocks = []
    for source in source_pack["sources"]:
        blocks.append(
            f"[{source['source_id']}] {source['title']}\n"
            f"Path: {source['path']}\n"
            f"Boundary: {source['claim_boundary']}\n"
            f"SHA-256: {source['sha256']}\n"
            f"---\n{source['content']}"
        )
    return "\n\n".join(blocks)


def validate_models(analyst_models: Iterable[str], synthesis_model: str) -> List[str]:
    analysts = [str(model).strip() for model in analyst_models if str(model).strip()]
    synthesis = str(synthesis_model).strip()
    if len(analysts) < 2:
        raise ValueError("At least two analyst models are required")
    if len(set(analysts)) != len(analysts):
        raise ValueError("Analyst model IDs must be distinct")
    if not synthesis:
        raise ValueError("A synthesis model is required")
    if synthesis in analysts:
        raise ValueError("The synthesis model must be distinct from every analyst model")
    return analysts


def validate_local_base_url(base_url: str) -> str:
    resolved = str(base_url or "").strip().rstrip("/")
    parsed = urlparse(resolved)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("LM Studio multi-model research requires a loopback HTTP endpoint")
    if not parsed.port:
        raise ValueError("LM Studio multi-model research requires an explicit local port")
    return resolved


def create_run(
    *,
    run_id: str,
    query: str,
    source_pack: Dict[str, Any],
    analyst_models: Iterable[str],
    synthesis_model: str,
    provider: str = "lm-studio",
    runtime_provider: str = "vllm",
    base_url: str = DEFAULT_LOCAL_BASE_URL,
    api_key_env: Optional[str] = None,
) -> Dict[str, Any]:
    analysts = validate_models(analyst_models, synthesis_model)
    if not query.strip():
        raise ValueError("Research query is required")
    return {
        "schema": SCHEMA,
        "kind": "multimodel",
        "research_id": run_id,
        "status": "queued",
        "stage": "queued",
        "query": query.strip(),
        "provider": provider,
        "runtime_provider": runtime_provider,
        "base_url": validate_local_base_url(base_url) if provider == "lm-studio" else (base_url or None),
        "credential_reference": api_key_env,
        "credential_required": bool(api_key_env),
        "source_pack_id": source_pack["pack_id"],
        "source_pack_sha256": source_pack["source_pack_sha256"],
        "sources": public_source_records(source_pack),
        "analyst_models": analysts,
        "synthesis_model": synthesis_model.strip(),
        "analyses": [],
        "synthesis": None,
        "claim_boundary": "Conclusion is bounded to the supplied repository evidence. Model agreement is not independent factual verification.",
        "timeline": [{"at": _now(), "event": "research.queued"}],
        "receipt_ids": [],
        "created_at": _now(),
        "updated_at": _now(),
        "completed_at": None,
        "run_sha256": None,
    }


def _analyst_messages(query: str, source_text: str, analyst_index: int) -> List[Dict[str, str]]:
    role = "evidence auditor" if analyst_index == 0 else "skeptical replication reviewer"
    return [
        {
            "role": "system",
            "content": (
                f"You are an independent {role}. Use only the supplied source pack. "
                "Do not assume a claim is true because another model may agree. Cite sources as [S1], [S2], etc. "
                "Separate supported observations from unsupported claims. Use no more than 120 words total. "
                "Write exactly four short sections: FINDINGS, CLAIM CEILING, GAPS, VERDICT. "
                "Finish every section; do not add an introduction."
            ),
        },
        {"role": "user", "content": f"RESEARCH QUESTION\n{query}\n\nSOURCE PACK\n{source_text}"},
    ]


def _synthesis_messages(query: str, source_text: str, analyses: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    analyst_text = "\n\n".join(
        f"ANALYST {index + 1} ({item['resolved_model']})\n{item['output']}"
        for index, item in enumerate(analyses)
    )
    return [
        {
            "role": "system",
            "content": (
                "You are the adjudicating synthesis model. The analyst outputs are untrusted interpretations, not sources. "
                "Check both against the supplied source pack. Use no more than 170 words total. Write exactly four short "
                "sections: CONCLUSION, SUPPORTED, DISAGREEMENT OR LIMITS, NEXT GATE. Finish every section. "
                "Cite repository sources as [S1], [S2], etc. "
                "Never promote test or demo evidence into a production, enterprise, security, or compliance claim."
            ),
        },
        {
            "role": "user",
            "content": (
                f"RESEARCH QUESTION\n{query}\n\nSOURCE PACK\n{source_text}\n\n"
                f"INDEPENDENT ANALYST OUTPUTS\n{analyst_text}"
            ),
        },
    ]


def _call_model(
    registry: ProviderRegistry,
    *,
    model: str,
    messages: List[Dict[str, str]],
    provider: str,
    runtime_provider: str,
    base_url: Optional[str],
    api_key_env: Optional[str],
    max_tokens: int,
) -> Dict[str, Any]:
    started_at = _now()
    prompt_sha256 = sha256_value(messages)
    response = registry.complete(
        messages,
        model,
        provider=runtime_provider,
        base_url=base_url,
        api_key_env=api_key_env,
        max_tokens=max_tokens,
        timeout_s=1800,
        max_retries=0,
    )
    output = str(response.content or "").strip()
    if not output:
        raise RuntimeError(f"Model {model} returned no visible output")
    resolved_model = str(response.model or model)
    return {
        "requested_model": model,
        "resolved_model": resolved_model,
        "provider": provider,
        "runtime_provider": runtime_provider,
        "base_url": base_url,
        "prompt_sha256": prompt_sha256,
        "response_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "usage": dict(response.usage or {}),
        "finish_reason": response.finish_reason,
        "output": output,
        "started_at": started_at,
        "completed_at": _now(),
    }


ProgressCallback = Callable[[Dict[str, Any], str, Dict[str, Any]], None]


def execute_run(
    run: Dict[str, Any],
    source_pack: Dict[str, Any],
    *,
    registry: Optional[ProviderRegistry] = None,
    progress: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    working = deepcopy(run)
    adapter_registry = registry or get_default_registry()
    source_text = _source_text(source_pack)

    def emit(event: str, payload: Dict[str, Any]) -> None:
        working["updated_at"] = _now()
        working["timeline"].append({"at": working["updated_at"], "event": event, **payload})
        if progress:
            progress(deepcopy(working), event, payload)

    working["status"] = "running"
    working["stage"] = "analysts"
    emit("research.started", {"model_count": len(working["analyst_models"]) + 1})
    try:
        for index, model in enumerate(working["analyst_models"]):
            emit("analysis.started", {"analyst_index": index, "requested_model": model})
            result = _call_model(
                adapter_registry,
                model=model,
                messages=_analyst_messages(working["query"], source_text, index),
                provider=working["provider"],
                runtime_provider=working["runtime_provider"],
                base_url=working.get("base_url"),
                api_key_env=working["credential_reference"],
                max_tokens=180,
            )
            result["analyst_index"] = index
            working["analyses"].append(result)
            emit(
                "analysis.completed",
                {
                    "analyst_index": index,
                    "requested_model": model,
                    "resolved_model": result["resolved_model"],
                    "response_sha256": result["response_sha256"],
                },
            )
        working["stage"] = "synthesis"
        emit("synthesis.started", {"requested_model": working["synthesis_model"]})
        synthesis = _call_model(
            adapter_registry,
            model=working["synthesis_model"],
            messages=_synthesis_messages(working["query"], source_text, working["analyses"]),
            provider=working["provider"],
            runtime_provider=working["runtime_provider"],
            base_url=working.get("base_url"),
            api_key_env=working["credential_reference"],
            max_tokens=260,
        )
        working["synthesis"] = synthesis
        emit(
            "synthesis.completed",
            {
                "requested_model": working["synthesis_model"],
                "resolved_model": synthesis["resolved_model"],
                "response_sha256": synthesis["response_sha256"],
            },
        )
        working["status"] = "completed"
        working["stage"] = "complete"
        working["completed_at"] = _now()
        emit("research.completed", {})
        working["run_sha256"] = sha256_value(run_hash_payload(working))
        return working
    except Exception as exc:
        working["status"] = "failed"
        working["stage"] = "failed"
        working["error"] = _safe_error(exc)
        emit("research.failed", {"error": working["error"]})
        return working
