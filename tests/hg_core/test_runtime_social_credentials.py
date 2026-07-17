from hg_core.security.runtime_social_credentials import (
    attach_runtime_proof_state,
    is_keystore_first_task,
    resolve_runtime_task_name,
    resolve_task_social_account_id,
    resolve_task_platform_credential,
)


def test_resolve_runtime_task_name_prefers_explicit(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_TASK_NAME", "ignored-task")
    assert resolve_runtime_task_name("newfoundland-bayman-fourclaw-engage") == "newfoundland-bayman-fourclaw-engage"


def test_is_keystore_first_task_identifies_bayman():
    assert is_keystore_first_task("newfoundland-bayman-fourclaw-engage") is True
    assert is_keystore_first_task("fourclaw-engage") is False


def test_resolve_task_platform_credential_reads_keystore_assignment(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_TASK_NAME", "newfoundland-bayman-fourclaw-engage")

    class FakeResolvedAccount:
        login_secret = '{"api_key":"bayman-fourclaw-key"}'

    class FakeService:
        def __init__(self, _provider):
            pass

        def resolve_task_social_account(self, task_name, tenant_id):
            assert task_name == "newfoundland-bayman-fourclaw-engage"
            return {"social_account_id": "acct-1"}

        def resolve_social_account(self, **kwargs):
            assert kwargs["social_account_id"] == "acct-1"
            assert kwargs["platform"] == "fourclaw"
            return FakeResolvedAccount()

    monkeypatch.setattr("hg_core.security.runtime_social_credentials.KeystoreService", FakeService)
    value = resolve_task_platform_credential(
        platform="fourclaw",
        credential_keys=("api_key", "token"),
    )
    assert value == "bayman-fourclaw-key"


def test_resolve_task_social_account_id_reads_keystore_assignment(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_TASK_NAME", "newfoundland-bayman-agentchan-auto-post")

    class FakeService:
        def __init__(self, _provider):
            pass

        def resolve_task_social_account(self, task_name, tenant_id):
            assert task_name == "newfoundland-bayman-agentchan-auto-post"
            assert tenant_id == "default"
            return {"social_account_id": "acct-agentchan", "platform": "agentchan"}

    monkeypatch.setattr("hg_core.security.runtime_social_credentials.KeystoreService", FakeService)
    value = resolve_task_social_account_id(platform="agentchan")
    assert value == "acct-agentchan"


def test_attach_runtime_proof_state_records_attached_artifact(monkeypatch):
    result = {"ok": True}

    monkeypatch.setattr(
        "hg_core.security.runtime_social_credentials.resolve_task_social_account_id",
        lambda **kwargs: "acct-moltbook",
    )

    attach_runtime_proof_state(
        result,
        platform="moltbook",
        task_name="newfoundland-bayman-moltbook-auto-post",
        tenant_id="tenant-a",
        persist_artifact=lambda social_account_id: {
            "artifact_type": "post_proof",
            "path": f"/tmp/{social_account_id}.json",
        },
    )

    assert result["proof_artifact"]["artifact_type"] == "post_proof"
    assert result["proof_state"] == {
        "platform": "moltbook",
        "tenant_id": "tenant-a",
        "task_name": "newfoundland-bayman-moltbook-auto-post",
        "keystore_first_task": True,
        "status": "attached",
        "social_account_id": "acct-moltbook",
        "binding_source": "task",
        "artifact_type": "post_proof",
        "artifact_path": "/tmp/acct-moltbook.json",
    }


def test_attach_runtime_proof_state_records_missing_binding(monkeypatch):
    result = {"ok": True}

    monkeypatch.setattr(
        "hg_core.security.runtime_social_credentials.resolve_task_social_account_id",
        lambda **kwargs: None,
    )

    attach_runtime_proof_state(
        result,
        platform="fourclaw",
        task_name="fourclaw-auto-post",
        tenant_id="tenant-a",
        persist_artifact=lambda social_account_id: {"artifact_type": "post_proof"},
    )

    assert "proof_artifact" not in result
    assert result["proof_state"]["status"] == "missing_binding"
    assert result["proof_state"]["reason"] == "no_resolved_social_account"


def test_attach_runtime_proof_state_records_binding_error(monkeypatch):
    result = {"ok": True}

    def _raise(**kwargs):
        raise RuntimeError("missing Bayman binding")

    monkeypatch.setattr(
        "hg_core.security.runtime_social_credentials.resolve_task_social_account_id",
        _raise,
    )

    attach_runtime_proof_state(
        result,
        platform="fourclaw",
        task_name="newfoundland-bayman-fourclaw-auto-post",
        tenant_id="tenant-a",
        persist_artifact=lambda social_account_id: {"artifact_type": "post_proof"},
    )

    assert result["proof_state"]["status"] == "binding_error"
    assert result["proof_state"]["reason"] == "missing Bayman binding"
    assert result["proof_artifact_error"] == "missing Bayman binding"
