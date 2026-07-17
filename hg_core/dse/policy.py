"""RealSinkPolicy — governed durable sink class definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from hg_core.dse import config as dse_config
from hg_core.dse.errors import REFUSED_SINK_NOT_IN_SCOPE, REFUSED_WRONG_SINK_CLASS


class SinkClass(str, Enum):
    DURABLE_LOCAL_FILE_SINK = "DURABLE_LOCAL_FILE_SINK"
    DURABLE_SQLITE_OR_STORE_SINK = "DURABLE_SQLITE_OR_STORE_SINK"
    LOCAL_INFERENCE_SINK = "LOCAL_INFERENCE_SINK"
    LOCAL_COMMAND_SANDBOX_SINK = "LOCAL_COMMAND_SANDBOX_SINK"
    LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK = "LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK"
    LOCAL_PUBLICATION_OUTBOX_SINK = "LOCAL_PUBLICATION_OUTBOX_SINK"
    PROCESS_SANDBOX_SINK = "PROCESS_SANDBOX_SINK"
    LOOP_SUPERVISOR_SINK = "LOOP_SUPERVISOR_SINK"


TRANCHE_SINK_MAP: Mapping[str, tuple[SinkClass, ...]] = {
    "DSE-FOUNDATION": tuple(SinkClass),
    "INFER-DSE": (SinkClass.LOCAL_INFERENCE_SINK,),
    "MEM-DSE": (SinkClass.DURABLE_SQLITE_OR_STORE_SINK,),
    "GMG-DSE": (SinkClass.DURABLE_SQLITE_OR_STORE_SINK,),
    "OEA-TER-DSE": (SinkClass.LOCAL_COMMAND_SANDBOX_SINK, SinkClass.DURABLE_LOCAL_FILE_SINK),
    "SRP-DSE": (SinkClass.DURABLE_LOCAL_FILE_SINK,),
    "SEN-DSE": (SinkClass.LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK,),
    "PUB-EXT-DSE": (SinkClass.LOCAL_PUBLICATION_OUTBOX_SINK,),
    "REB-DSE": (SinkClass.DURABLE_LOCAL_FILE_SINK,),
    "RIB-DSE": (SinkClass.PROCESS_SANDBOX_SINK,),
    "ALOOP-DSE": (SinkClass.LOOP_SUPERVISOR_SINK,),
}


@dataclass(frozen=True)
class RealSinkPolicy:
    sink_class: SinkClass
    tranche_id: str
    requires_gpp: bool = False
    requires_ueak: bool = False
    requires_rollback: bool = True
    bounded_timeout_s: float | None = None
    allow_network: bool = False

    def is_in_scope(self) -> bool:
        allowed = TRANCHE_SINK_MAP.get(self.tranche_id, ())
        return self.sink_class in allowed

    def validate_scope(self) -> tuple[bool, str]:
        if not self.is_in_scope():
            return False, REFUSED_SINK_NOT_IN_SCOPE
        return True, ""

    @staticmethod
    def sandbox_root_for(sink_class: SinkClass):
        mapping = {
            SinkClass.DURABLE_LOCAL_FILE_SINK: dse_config.dse_file_sink_root,
            SinkClass.DURABLE_SQLITE_OR_STORE_SINK: dse_config.dse_store_sink_root,
            SinkClass.LOCAL_INFERENCE_SINK: dse_config.dse_inference_sink_root,
            SinkClass.LOCAL_COMMAND_SANDBOX_SINK: dse_config.dse_command_sandbox_root,
            SinkClass.LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK: dse_config.dse_sensor_sink_root,
            SinkClass.LOCAL_PUBLICATION_OUTBOX_SINK: dse_config.dse_outbox_root,
            SinkClass.PROCESS_SANDBOX_SINK: dse_config.dse_process_sandbox_root,
            SinkClass.LOOP_SUPERVISOR_SINK: dse_config.dse_loop_supervisor_root,
        }
        factory = mapping.get(sink_class)
        return factory() if factory else dse_config.dse_sandbox_root()


def refuse_wrong_sink_class(*, expected: SinkClass, actual: SinkClass) -> str:
    if expected != actual:
        return REFUSED_WRONG_SINK_CLASS
    return ""


__all__ = ["RealSinkPolicy", "SinkClass", "TRANCHE_SINK_MAP", "refuse_wrong_sink_class"]
