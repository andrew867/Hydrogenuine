"""Vector Memory Store with namespace isolation and provider abstraction."""

from __future__ import annotations

import hashlib
from typing import Any

from hg_core.storage_substrate.common import SCHEMA_VERSION, authority_fields, require_non_authority, stable_hash, stable_json
from hg_core.storage_substrate.sds import StructuredDataStore

PROVIDER_STATUS_AVAILABLE = "available"
PROVIDER_STATUS_UNAVAILABLE = "unavailable"
PROVIDER_STATUS_ADVISORY_ONLY = "advisory_only"


def deterministic_embedding(text: str, dimension: int = 4) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [round(digest[i] / 255.0, 6) for i in range(dimension)]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in values) + "]"


class EmbeddingProviderContract:
    """Abstract contract for embedding providers (deterministic fixture, OpenVINO, Ollama, vLLM)."""

    def __init__(self, provider_id: str, model_id: str, *, status: str = PROVIDER_STATUS_AVAILABLE, advisory_only: bool = True):
        self.provider_id = provider_id
        self.model_id = model_id
        self.status = status
        self.advisory_only = advisory_only

    def embed(self, text: str, dimension: int = 4) -> list[float]:
        if self.status == PROVIDER_STATUS_UNAVAILABLE:
            raise ProviderUnavailableError(f"provider {self.provider_id} is unavailable")
        return deterministic_embedding(text, dimension)

    def provider_metadata(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "status": self.status,
            "advisory_only": self.advisory_only,
            "health_is_authority": False,
            "output_is_truth": False,
            **authority_fields(),
        }


class ProviderUnavailableError(RuntimeError):
    pass


class VectorMemoryStore:
    def __init__(self, dsn: str | None = None, *, provider: EmbeddingProviderContract | None = None):
        self.sds = StructuredDataStore(dsn)
        self.provider = provider or EmbeddingProviderContract(
            provider_id="deterministic_fixture",
            model_id="deterministic_fixture_embedding_v1",
        )

    def extension_available(self) -> bool:
        with self.sds.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                row = cur.fetchone()
        return bool(row and row[0])

    def insert_record(
        self,
        record_id: str,
        source_ref: str,
        text: str,
        payload: dict[str, Any],
        *,
        namespace: str = "default",
    ) -> dict[str, Any]:
        require_non_authority(payload)
        embedding = self.provider.embed(text)
        record = {
            "schema_version": SCHEMA_VERSION,
            "record_id": record_id,
            "namespace": namespace,
            "source_ref": source_ref,
            "model_id": self.provider.model_id,
            "provider": self.provider.provider_id,
            "dimension": len(embedding),
            "embedding": embedding,
            "payload": payload,
            "retention_class": "AUDIT_RETENTION",
            **authority_fields(),
        }
        record_hash = stable_hash(record)
        with self.sds.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vector_memory_records(record_id, namespace, source_ref, model_id, provider, dimension, embedding, payload, retention_class, hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb, %s, %s)
                    ON CONFLICT (record_id) DO UPDATE
                    SET namespace = EXCLUDED.namespace,
                        source_ref = EXCLUDED.source_ref,
                        model_id = EXCLUDED.model_id,
                        provider = EXCLUDED.provider,
                        dimension = EXCLUDED.dimension,
                        embedding = EXCLUDED.embedding,
                        payload = EXCLUDED.payload,
                        retention_class = EXCLUDED.retention_class,
                        hash = EXCLUDED.hash
                    """,
                    (
                        record_id,
                        namespace,
                        source_ref,
                        self.provider.model_id,
                        self.provider.provider_id,
                        len(embedding),
                        vector_literal(embedding),
                        stable_json(payload),
                        "AUDIT_RETENTION",
                        record_hash,
                    ),
                )
            conn.commit()
        record["hash"] = record_hash
        return record

    def query(self, text: str, limit: int = 3, *, namespace: str | None = None) -> list[dict[str, Any]]:
        embedding = vector_literal(self.provider.embed(text))
        with self.sds.connect() as conn:
            with conn.cursor() as cur:
                if namespace is not None:
                    cur.execute(
                        """
                        SELECT record_id, source_ref, payload, embedding <-> %s::vector AS distance, hash, namespace, model_id, provider
                        FROM vector_memory_records
                        WHERE namespace = %s
                        ORDER BY embedding <-> %s::vector
                        LIMIT %s
                        """,
                        (embedding, namespace, embedding, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT record_id, source_ref, payload, embedding <-> %s::vector AS distance, hash, namespace, model_id, provider
                        FROM vector_memory_records
                        ORDER BY embedding <-> %s::vector
                        LIMIT %s
                        """,
                        (embedding, embedding, limit),
                    )
                rows = cur.fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            result = {
                "record_id": row[0],
                "source_ref": row[1],
                "payload": row[2],
                "distance": float(row[3]),
                "source_hash": row[4],
                "namespace": row[5],
                "model_id": row[6],
                "provider": row[7],
                "similarity_score": max(0.0, 1.0 - float(row[3])),
                "uncertainty": "embedding_distance_is_approximate",
                "similarity_is_truth": False,
                "similarity_is_permission": False,
                **authority_fields(),
            }
            results.append(result)
        return results

    def provider_status(self) -> dict[str, Any]:
        return self.provider.provider_metadata()
