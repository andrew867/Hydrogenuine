"""DSE tranche gate feature checks."""

from __future__ import annotations

from hg_core.dse.tranche_checks import build_tranche_checks
from hg_runtime.durable_side_effect.loop_sink import TRANCHE_ID as ALOOP_TR
from hg_runtime.durable_side_effect.loop_sink import load_aloop_dse_fixtures, process_aloop_dse_bundle
from hg_runtime.durable_side_effect.command_sink import load_oea_ter_dse_fixtures, process_oea_ter_dse_bundle
from hg_runtime.durable_side_effect.fixtures import FIXTURE_CLOCK
from hg_runtime.durable_side_effect.grant_sink import TRANCHE_ID as GMG_ID
from hg_runtime.durable_side_effect.grant_sink import load_gmg_dse_fixtures, process_gmg_dse_bundle
from hg_runtime.durable_side_effect.infer_sink import TRANCHE_ID as INFER_ID
from hg_runtime.durable_side_effect.infer_sink import load_infer_dse_fixtures, process_infer_dse_bundle
from hg_runtime.durable_side_effect.command_sink import TRANCHE_ID as OEA_ID
from hg_runtime.durable_side_effect.mem_sink import TRANCHE_ID as MEM_ID
from hg_runtime.durable_side_effect.mem_sink import load_mem_dse_fixtures, process_mem_dse_bundle
from hg_runtime.durable_side_effect.outbox_sink import TRANCHE_ID as PUB_ID
from hg_runtime.durable_side_effect.outbox_sink import load_pub_ext_dse_fixtures, process_pub_ext_dse_bundle
from hg_runtime.durable_side_effect.process_sink import TRANCHE_ID as RIB_ID
from hg_runtime.durable_side_effect.process_sink import load_rib_dse_fixtures, process_rib_dse_bundle
from hg_runtime.durable_side_effect.restore_sink import TRANCHE_ID as REB_ID
from hg_runtime.durable_side_effect.restore_sink import load_reb_dse_fixtures, process_reb_dse_bundle
from hg_runtime.durable_side_effect.sensor_sink import TRANCHE_ID as SEN_ID
from hg_runtime.durable_side_effect.sensor_sink import load_sen_dse_fixtures, process_sen_dse_bundle
from hg_runtime.durable_side_effect.srp_sink import TRANCHE_ID as SRP_ID
from hg_runtime.durable_side_effect.srp_sink import load_srp_dse_fixtures, process_srp_dse_bundle


def run_infer_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=INFER_ID,
        load_fixtures=load_infer_dse_fixtures,
        process_bundle=process_infer_dse_bundle,
        valid_bundle_id="infer-dse-valid",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("tep_wrapped"), dict),
    )


def run_mem_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=MEM_ID,
        load_fixtures=load_mem_dse_fixtures,
        process_bundle=process_mem_dse_bundle,
        valid_bundle_id="mem-dse-valid",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("readback_proof"), dict),
    )


def run_gmg_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=GMG_ID,
        load_fixtures=load_gmg_dse_fixtures,
        process_bundle=process_gmg_dse_bundle,
        valid_bundle_id="gmg-dse-valid-create",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("grant_receipt"), dict),
    )


def run_oea_ter_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=OEA_ID,
        load_fixtures=load_oea_ter_dse_fixtures,
        process_bundle=process_oea_ter_dse_bundle,
        valid_bundle_id="oea-dse-valid",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("command_receipt"), dict),
    )


def run_srp_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=SRP_ID,
        load_fixtures=load_srp_dse_fixtures,
        process_bundle=process_srp_dse_bundle,
        valid_bundle_id="srp-dse-valid-apply",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: r.get("restrict_only") is True,
    )


def run_sen_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=SEN_ID,
        load_fixtures=load_sen_dse_fixtures,
        process_bundle=process_sen_dse_bundle,
        valid_bundle_id="sen-dse-valid-fixture",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("tep_wrapped"), dict),
    )


def run_pub_ext_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=PUB_ID,
        load_fixtures=load_pub_ext_dse_fixtures,
        process_bundle=process_pub_ext_dse_bundle,
        valid_bundle_id="pub-dse-valid-stage",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("outbox_receipt"), dict),
    )


def run_reb_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=REB_ID,
        load_fixtures=load_reb_dse_fixtures,
        process_bundle=process_reb_dse_bundle,
        valid_bundle_id="reb-dse-valid",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("restore_receipt"), dict),
    )


def run_rib_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=RIB_ID,
        load_fixtures=load_rib_dse_fixtures,
        process_bundle=process_rib_dse_bundle,
        valid_bundle_id="rib-dse-valid",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("process_receipt"), dict),
    )


def run_aloop_dse_checks() -> dict[str, object]:
    return build_tranche_checks(
        tranche_id=ALOOP_TR,
        load_fixtures=load_aloop_dse_fixtures,
        process_bundle=process_aloop_dse_bundle,
        valid_bundle_id="aloop-dse-valid",
        observed_at=FIXTURE_CLOCK,
        extra_valid_assert=lambda r: isinstance(r.get("loop_receipt"), dict),
    )


__all__ = [
    "run_aloop_dse_checks",
    "run_gmg_dse_checks",
    "run_infer_dse_checks",
    "run_mem_dse_checks",
    "run_oea_ter_dse_checks",
    "run_pub_ext_dse_checks",
    "run_reb_dse_checks",
    "run_rib_dse_checks",
    "run_sen_dse_checks",
    "run_srp_dse_checks",
]
