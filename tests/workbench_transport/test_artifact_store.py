"""Bounded artifact store unit tests (WBT cases 1-6)."""
from __future__ import annotations

import hashlib

import pytest

from hg_workbench.artifact_store import (
    ArtifactStoreError, ArtifactTooLargeError, StoredArtifact, max_upload_bytes,
    read_in_chunks, sanitize_filename, store_upload,
)

AID = "wba-0123456789abcdef"


def test_case1_sanitize_strips_traversal_and_separators():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a/b\\c.txt") == "c.txt"
    assert sanitize_filename("...hidden") == "hidden"
    assert sanitize_filename("na\x00me .bin") == "name_.bin"
    assert sanitize_filename("") == "upload.bin"
    assert sanitize_filename("/") == "upload.bin"
    # length bound
    assert len(sanitize_filename("x" * 500)) <= 128


def test_case2_store_computes_server_sha256_and_size(tmp_path):
    data = b"hello workbench bytes"
    stored = store_upload(run_dir=tmp_path, artifact_id=AID, filename="a.txt",
                          chunks=read_in_chunks(data))
    assert isinstance(stored, StoredArtifact)
    assert stored.content_hash == "sha256:" + hashlib.sha256(data).hexdigest()
    assert stored.size_bytes == len(data)
    assert stored.stored_path_ref == f"artifacts/{AID}_a.txt"
    # bytes are on disk, exactly as uploaded
    assert (tmp_path / "artifacts" / f"{AID}_a.txt").read_bytes() == data
    # the returned metadata never contains the raw bytes
    assert data not in repr(stored).encode()


def test_case3_cap_enforced_partial_removed(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKBENCH_MAX_UPLOAD_BYTES", "8")
    with pytest.raises(ArtifactTooLargeError):
        store_upload(run_dir=tmp_path, artifact_id=AID, filename="big.bin",
                     chunks=read_in_chunks(b"0123456789", size=4))
    # partial file removed on overflow
    assert not (tmp_path / "artifacts" / f"{AID}_big.bin").exists()


def test_case4_explicit_max_bytes_arg_overrides(tmp_path):
    with pytest.raises(ArtifactTooLargeError):
        store_upload(run_dir=tmp_path, artifact_id=AID, filename="x", chunks=[b"abc"],
                     max_bytes=2)


def test_case5_containment_and_bad_id(tmp_path):
    with pytest.raises(ArtifactStoreError) as e:
        store_upload(run_dir=tmp_path, artifact_id="not-an-id", filename="x",
                     chunks=[b"y"])
    assert e.value.code == "bad_artifact_id"
    # even a hostile filename cannot escape the artifacts dir
    stored = store_upload(run_dir=tmp_path, artifact_id=AID,
                          filename="../../escape.txt", chunks=[b"z"])
    resolved = (tmp_path / "artifacts").resolve()
    assert resolved in (tmp_path / stored.stored_path_ref).resolve().parents


def test_case6_default_cap_is_conservative(monkeypatch):
    monkeypatch.delenv("HG_WORKBENCH_MAX_UPLOAD_BYTES", raising=False)
    assert max_upload_bytes() == 25 * 1024 * 1024
    monkeypatch.setenv("HG_WORKBENCH_MAX_UPLOAD_BYTES", "0")
    assert max_upload_bytes() == 25 * 1024 * 1024  # non-positive -> default
    monkeypatch.setenv("HG_WORKBENCH_MAX_UPLOAD_BYTES", "garbage")
    assert max_upload_bytes() == 25 * 1024 * 1024
