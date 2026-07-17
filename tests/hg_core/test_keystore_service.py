from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

import pytest

from hg_core.security.keystore import (
    KeystoreService,
    SecretAliasDisabledError,
    SecretAliasNotFoundError,
    SecretResolutionError,
    SocialAccountBindingError,
    SocialAccountNotFoundError,
    SocialAccountStateError,
)
from hg_core.security.secrets_provider import SecretsProvider
from hg_gateway import keystore_repo


class DictSecretsProvider(SecretsProvider):
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get(self, key: str) -> Optional[str]:
        return self._values.get(key)


@pytest.fixture
def gateway_db(monkeypatch):
    root = Path(".pytest-tmp-keystore") / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    try:
        yield db_path
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resolve_social_account_success(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.secret_alias_create(
        alias_id="alias-mfa",
        provider_kind="env",
        provider_ref="fb_mfa_secret",
        purpose="facebook_mfa",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        mfa_secret_alias_id="alias-mfa",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )

    service = KeystoreService(
        DictSecretsProvider(
            {
                "fb_login_secret": "user@example.com|password123",
                "fb_mfa_secret": "123456",
            }
        )
    )
    resolved = service.resolve_social_account(
        account_alias="fb-main",
        tenant_id="tenant-a",
        platform="facebook",
        entity_id="entity-1",
    )

    assert resolved.social_account_id == "acct-1"
    assert resolved.account_alias == "fb-main"
    assert resolved.login_secret == "user@example.com|password123"
    assert resolved.mfa_secret == "123456"


def test_resolve_social_account_missing_alias_fails_closed(gateway_db):
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="missing-alias",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({}))

    with pytest.raises(SecretAliasNotFoundError):
        service.resolve_social_account(
            account_alias="fb-main",
            tenant_id="tenant-a",
            platform="facebook",
            entity_id="entity-1",
        )


def test_resolve_social_account_disabled_alias_fails_closed(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.secret_alias_disable("alias-login", db_path=str(gateway_db))
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"}))

    with pytest.raises(SecretAliasDisabledError):
        service.resolve_social_account(
            account_alias="fb-main",
            tenant_id="tenant-a",
            platform="facebook",
            entity_id="entity-1",
        )


def test_resolve_social_account_missing_secret_value_fails_closed(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({}))

    with pytest.raises(SecretResolutionError):
        service.resolve_social_account(
            account_alias="fb-main",
            tenant_id="tenant-a",
            platform="facebook",
            entity_id="entity-1",
        )


def test_get_social_account_rejects_wrong_entity_scope(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="active",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"}))

    with pytest.raises(SocialAccountStateError):
        service.get_social_account(
            account_alias="fb-main",
            tenant_id="tenant-a",
            platform="facebook",
            entity_id="entity-2",
        )


def test_get_social_account_rejects_locked_state(gateway_db):
    keystore_repo.secret_alias_create(
        alias_id="alias-login",
        provider_kind="env",
        provider_ref="fb_login_secret",
        purpose="facebook_login",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="facebook",
        account_alias="fb-main",
        login_secret_alias_id="alias-login",
        entity_scope="entity-1",
        state="locked",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({"fb_login_secret": "user@example.com|password123"}))

    with pytest.raises(SocialAccountStateError):
        service.get_social_account(
            account_alias="fb-main",
            tenant_id="tenant-a",
            platform="facebook",
            entity_id="entity-1",
        )


def test_get_social_account_missing_record_raises(gateway_db):
    service = KeystoreService(DictSecretsProvider({}))

    with pytest.raises(SocialAccountNotFoundError):
        service.get_social_account(account_alias="missing", tenant_id="tenant-a")


def test_resolve_task_social_account_uses_operational_binding(gateway_db):
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({}))

    account = service.resolve_task_social_account(
        "newfoundland-bayman-fourclaw-engage",
        tenant_id="tenant-a",
    )

    assert account["account_alias"] == "bayman-fourclaw"
    assert account["entity_scope"] == "newfoundland-bayman"


def test_resolve_task_social_account_fails_when_ambiguous(gateway_db):
    keystore_repo.social_account_create(
        social_account_id="acct-1",
        tenant_id="tenant-a",
        platform="fourclaw",
        account_alias="bayman-fourclaw-a",
        entity_scope="newfoundland-bayman",
        state="verified",
        db_path=str(gateway_db),
    )
    keystore_repo.social_account_create(
        social_account_id="acct-2",
        tenant_id="tenant-a",
        platform="fourclaw",
        account_alias="bayman-fourclaw-b",
        entity_scope="newfoundland-bayman",
        state="active",
        db_path=str(gateway_db),
    )
    service = KeystoreService(DictSecretsProvider({}))

    with pytest.raises(SocialAccountBindingError):
        service.resolve_task_social_account(
            "newfoundland-bayman-fourclaw-engage",
            tenant_id="tenant-a",
        )
