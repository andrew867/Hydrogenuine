"""CT-02 SEC-U7 TER secret path jail tests."""

from __future__ import annotations

from pathlib import Path

from hg_ter.executor import TERExecutor
from hg_ter.types import TERConfig


def _executor(tmp_path: Path) -> TERExecutor:
    return TERExecutor(TERConfig(repo_root=tmp_path, artifact_root=tmp_path / "artifacts"))


def test_sec_u7_env_read_refused(tmp_path) -> None:
    executor = _executor(tmp_path)
    request = executor.make_request(
        ("type", ".env"),
        requested_by="sec:test",
        purpose="secret_jail_test",
        cwd=str(tmp_path),
    )
    receipt, outcome = executor.execute(request)
    assert receipt.result_status == "refused"
    assert outcome.reason_code == "TER_JAIL_VIOLATION"


def test_sec_u7_credentials_path_refused(tmp_path) -> None:
    executor = _executor(tmp_path)
    cred = tmp_path / "credentials"
    cred.mkdir()
    (cred / "key.txt").write_text("secret", encoding="utf-8")
    request = executor.make_request(
        ("type", str(cred / "key.txt")),
        requested_by="sec:test",
        purpose="secret_jail_test",
        cwd=str(tmp_path),
    )
    receipt, outcome = executor.execute(request)
    assert receipt.result_status == "refused"
    assert receipt.refusal_reason == "TER_JAIL_VIOLATION"
    assert outcome.reason_code == "TER_JAIL_VIOLATION"
