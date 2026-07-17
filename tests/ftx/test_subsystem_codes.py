"""CT-05 FTX-I1 subsystem canonical code assertions."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.failures.registry import validate_reason_code
from hg_ter.executor import TERExecutor
from hg_ter.types import TERConfig


def test_iam_scope_deny_canonical() -> None:
    result = validate_operator_authority("op:forged", scope="approve_change")
    mapped = validate_reason_code(result.reason_code)
    assert mapped.ok
    assert mapped.record is not None
    assert mapped.record.state == "denied"


def test_ter_jail_canonical(tmp_path) -> None:
    executor = TERExecutor(TERConfig(repo_root=tmp_path, artifact_root=tmp_path / "art"))
    request = executor.make_request(("type", ".env"), requested_by="t", purpose="t", cwd=str(tmp_path))
    receipt, outcome = executor.execute(request)
    mapped = validate_reason_code(receipt.refusal_reason or outcome.reason_code)
    assert mapped.ok
    assert mapped.record is not None
    assert mapped.record.code == "ter.refused.jail_violation"
