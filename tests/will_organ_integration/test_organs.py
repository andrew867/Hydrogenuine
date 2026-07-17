"""Organ WILL integration tests."""

from hg_runtime.will_module.agent0 import build_agent0_will_context
from hg_runtime.will_module.organs import ORGAN_WILL_EFFECTS, attach_will_to_organs


def test_organs_receive_advisory_context():
    ctx = build_agent0_will_context(run_id="run-organ", will_profile="configs/will/agent0_dev_boot_will.example.json")
    organs = attach_will_to_organs(ctx.will_context, ["organ:Agent0", "organ:AIS", "organ:AuthorityObserver"])
    assert len(organs) == 3
    for organ in organs:
        payload = organ.to_payload()
        assert payload["may_authorize"] is False
        assert payload["permission_granted"] is False
        assert payload["advisory_only"] is True


def test_organ_effect_map_complete():
    assert ORGAN_WILL_EFFECTS["organ:ToolBrokerObserver"] == "request_context_only"
    assert ORGAN_WILL_EFFECTS["organ:AuthorityObserver"] == "verify_no_authorization"
