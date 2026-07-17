"""DTX DIB-to-LEB bridge helpers."""

from __future__ import annotations

from hg_runtime.document_text_exchange.document_corpus import build_dtx_leb_bridge_record


def build_bridge_records(*, extraction_receipts: list[dict], dib_adapters: list[dict]) -> list[dict]:
    adapter_by_source = {row["source_id"]: row for row in dib_adapters}
    bridge_records: list[dict] = []
    for idx, receipt in enumerate(extraction_receipts):
        source_id = receipt["source_id"]
        adapter = adapter_by_source.get(source_id)
        if not adapter:
            continue
        bridge_records.append(
            build_dtx_leb_bridge_record(
                bridge_id=f"dtx-bridge-{idx:03d}",
                fixture_id=receipt["file_id"],
                adapter_record_id=adapter["adapter_id"],
                source_id=source_id,
            )
        )
    return bridge_records
