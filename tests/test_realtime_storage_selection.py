from __future__ import annotations

from hg_realtime.integrations.idempotency_store import GatewayIdempotencyStore, SqliteIdempotencyStore, default_idempotency_store
from hg_realtime.integrations.run_index import GatewayRunIndexWriter, SqliteRunIndexWriter, default_run_index_reader, default_run_index_writer
from hg_realtime.leases.store import GatewayRunLeaseStore, RunLeaseStore, default_lease_store
from hg_realtime.steering.store import GatewaySteeringStore, SqliteSteeringStore, default_steering_store


def test_default_runtime_stores_use_gateway_backend_when_configured(monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    assert isinstance(default_steering_store(), GatewaySteeringStore)
    assert isinstance(default_lease_store(), GatewayRunLeaseStore)
    assert isinstance(default_run_index_writer(), GatewayRunIndexWriter)
    assert isinstance(default_run_index_reader(), GatewayRunIndexWriter)
    assert isinstance(default_idempotency_store(), GatewayIdempotencyStore)


def test_default_runtime_stores_keep_explicit_sqlite_compatibility(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    assert isinstance(default_steering_store(str(tmp_path / "steering.sqlite")), SqliteSteeringStore)
    assert isinstance(default_lease_store(str(tmp_path / "leases.sqlite")), RunLeaseStore)
    assert isinstance(default_run_index_writer(str(tmp_path / "runs.sqlite")), SqliteRunIndexWriter)
    assert isinstance(default_idempotency_store(str(tmp_path / "idem.sqlite")), SqliteIdempotencyStore)
