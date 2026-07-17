from __future__ import annotations

import json

from hg_runtime.social_capability.legacy_import import import_legacy_rules
from hg_runtime.social_capability.permit_templates import MigrationClass


def test_legacy_rules_inventoried():
    result = import_legacy_rules()
    assert len(result.inventory) >= 10


def test_engage_rules_rejected_unsafe():
    result = import_legacy_rules()
    engage_rejected = [r for r in result.rejected if r.mode == "reply"]
    assert len(engage_rejected) >= 4


def test_migrated_templates_not_permission():
    result = import_legacy_rules()
    assert result.migrated_templates
    for t in result.migrated_templates:
        payload = t.to_payload()
        assert payload["permission_granted"] is False
        assert payload["authority_created"] is False
        assert payload["publish_allowed_default"] is False


def test_stale_or_superseded_not_migrated_as_publish():
    result = import_legacy_rules()
    for t in result.migrated_templates:
        assert t.allowed_action_type.value in ("read", "draft", "queue")


def test_template_hash_stable():
    result = import_legacy_rules()
    t = result.migrated_templates[0]
    assert t.to_payload()["template_hash"] == t.to_payload()["template_hash"]


def test_no_credentials_in_templates():
    result = import_legacy_rules()
    for t in result.migrated_templates:
        blob = json.dumps(t.to_payload()).lower()
        assert "api_key" not in blob
        assert "bearer" not in blob
        assert "password" not in blob
