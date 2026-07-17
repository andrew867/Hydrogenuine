"""EGI no-authority enforcement tests."""

from __future__ import annotations

import pytest

from hg_core.egi.errors import (
    DENIED_AUTHORITY_CONVERSION,
    DENIED_PRAISE_AS_APPROVAL,
    DENIED_SELF_MODIFICATION,
    DENIED_TOOL_GRANT,
    EGIValidationError,
)
from hg_core.egi.no_authority import (
    assert_forbidden_authority_action,
    check_package_import_fences,
    refuse_praise_as_approval,
    refuse_self_modification,
    refuse_tool_grant,
)


def test_forbidden_authority_actions():
    for action in ("mint_gpp_permit", "call_oea", "call_ter", "approve_ueak_execution", "deploy"):
        with pytest.raises(EGIValidationError) as exc:
            assert_forbidden_authority_action(action)
        assert exc.value.args[0] == DENIED_AUTHORITY_CONVERSION


def test_refuse_tool_grant():
    with pytest.raises(EGIValidationError) as exc:
        refuse_tool_grant()
    assert exc.value.args[0] == DENIED_TOOL_GRANT


def test_refuse_self_modification():
    with pytest.raises(EGIValidationError) as exc:
        refuse_self_modification(target_path="hg_core/egi/runtime/engine.py")
    assert exc.value.args[0] == DENIED_SELF_MODIFICATION


def test_praise_is_not_approval():
    with pytest.raises(EGIValidationError) as exc:
        refuse_praise_as_approval("good job, ship it")
    assert exc.value.args[0] == DENIED_PRAISE_AS_APPROVAL


def test_package_import_fences():
    ok, failures = check_package_import_fences()
    assert ok, failures


def test_egi_cannot_lower_safety_via_forbidden_action():
    with pytest.raises(EGIValidationError):
        assert_forbidden_authority_action("lower_safety_boundary")
