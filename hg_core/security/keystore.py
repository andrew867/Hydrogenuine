"""
Provider-backed keystore service and secret alias resolution (Social Media Entity Tools).
Resolves login/mfa credentials via SecretsProvider; alias_id -> provider_ref resolution
can be provided by a repository (see Phase 2.2 gateway repository).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from hg_core.security.secrets_provider import SecretsProvider
from hg_gateway import keystore_repo


class KeystoreError(RuntimeError):
    """Base class for keystore failures."""


class SocialAccountNotFoundError(KeystoreError):
    """The requested social account does not exist."""


class SecretAliasNotFoundError(KeystoreError):
    """A required secret alias does not exist."""


class SecretAliasDisabledError(KeystoreError):
    """A required secret alias has been disabled."""


class SecretResolutionError(KeystoreError):
    """Secret resolution failed or returned an empty value."""


class SocialAccountStateError(KeystoreError):
    """The social account is not usable in its current state."""


class SocialAccountBindingError(KeystoreError):
    """The runtime task does not have a valid social-account binding contract."""


@dataclass
class SocialAccountBinding:
    """Binding of a social account to secret refs (env key or alias_id resolved via repository)."""
    platform: str
    account_alias: str
    login_secret_ref: str
    mfa_secret_ref: Optional[str] = None


@dataclass
class ResolvedSocialAccount:
    """Resolved social account plus secrets for runtime use."""

    social_account_id: str
    tenant_id: str
    platform: str
    account_alias: str
    entity_scope: Optional[str]
    persona_scope: Optional[str]
    state: str
    login_secret: str
    mfa_secret: Optional[str]
    login_secret_alias_id: Optional[str]
    mfa_secret_alias_id: Optional[str]


class KeystoreService:
    """
    Resolve secrets via a SecretsProvider. provider_ref is passed to provider.get(provider_ref).
    When using secret_aliases, resolve alias_id -> provider_ref via a repository then call resolve.
    """

    def __init__(self, secrets_provider: SecretsProvider) -> None:
        self._provider = secrets_provider

    def resolve(self, provider_ref: str) -> Optional[str]:
        """Resolve a single secret by provider_ref (e.g. env var name or key)."""
        return self._provider.get(provider_ref)

    def resolve_login(self, binding: SocialAccountBinding) -> tuple[Optional[str], Optional[str]]:
        """Resolve login and optional MFA secrets for a social account binding."""
        login = self.resolve(binding.login_secret_ref)
        mfa = self.resolve(binding.mfa_secret_ref) if binding.mfa_secret_ref else None
        return login, mfa

    def resolve_alias(self, alias_id: str) -> str:
        """Resolve a secret alias to a provider-backed secret value."""
        alias = keystore_repo.secret_alias_get(alias_id)
        if not alias:
            raise SecretAliasNotFoundError(f"Secret alias not found: {alias_id}")
        if alias.get("disabled_at"):
            raise SecretAliasDisabledError(f"Secret alias disabled: {alias_id}")
        provider_ref = (alias.get("provider_ref") or "").strip()
        if not provider_ref:
            raise SecretResolutionError(f"Secret alias missing provider ref: {alias_id}")
        value = self.resolve(provider_ref)
        if not value:
            raise SecretResolutionError(f"Secret value missing for alias: {alias_id}")
        return value

    def get_social_account(
        self,
        *,
        social_account_id: Optional[str] = None,
        account_alias: Optional[str] = None,
        tenant_id: str = "default",
        platform: Optional[str] = None,
        entity_id: Optional[str] = None,
        allow_states: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """Load and validate a social account by id or alias."""
        if social_account_id:
            account = keystore_repo.social_account_get(social_account_id, tenant_id=tenant_id)
        elif account_alias:
            account = keystore_repo.social_account_get_by_alias(account_alias, tenant_id=tenant_id)
        else:
            raise SocialAccountNotFoundError("No social account identifier provided")
        if not account:
            ident = social_account_id or account_alias or "unknown"
            raise SocialAccountNotFoundError(f"Social account not found: {ident}")
        if platform and (account.get("platform") or "").lower() != platform.lower():
            raise SocialAccountStateError(
                f"Social account platform mismatch: expected {platform}, got {account.get('platform')}"
            )
        if entity_id:
            scope = (account.get("entity_scope") or "").strip()
            if scope and scope != entity_id:
                raise SocialAccountStateError(
                    f"Social account {account.get('account_alias')} is not assigned to entity {entity_id}"
                )
        state = (account.get("state") or "").strip().lower()
        usable_states = allow_states or {"active", "verified", "pending", "unverified"}
        if state and state not in usable_states:
            raise SocialAccountStateError(
                f"Social account {account.get('account_alias')} is not usable in state {account.get('state')}"
            )
        return account

    def resolve_task_social_account(
        self,
        task_name: str,
        *,
        tenant_id: str = "default",
        allow_states: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """Resolve the single assigned social account for a runtime task."""
        try:
            from hg_core.job_registry import get_operational_binding
        except Exception as exc:
            raise SocialAccountBindingError(f"Unable to load operational binding for task {task_name}") from exc

        binding = get_operational_binding(task_name) or {}
        platform = str(binding.get("platform") or "").strip()
        operational_agent_id = str(binding.get("operational_agent_id") or "").strip()
        fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
        if not platform or not operational_agent_id:
            raise SocialAccountBindingError(f"Task {task_name} does not have an operational social-account binding")

        accounts = keystore_repo.social_account_list(tenant_id=tenant_id, platform=platform)
        matches = [
            account
            for account in accounts
            if str(account.get("entity_scope") or "").strip() == operational_agent_id
            or (fingerprint_id and str(account.get("persona_scope") or "").strip() == fingerprint_id)
        ]
        if not matches:
            raise SocialAccountNotFoundError(
                f"No social account assigned for task {task_name} ({platform}/{operational_agent_id})"
            )

        usable_states = {state.strip().lower() for state in (allow_states or {"active", "verified", "pending", "unverified"})}
        usable_matches = [
            account for account in matches if str(account.get("state") or "").strip().lower() in usable_states
        ]
        if not usable_matches:
            raise SocialAccountStateError(
                f"No usable social account assigned for task {task_name} ({platform}/{operational_agent_id})"
            )
        if len(usable_matches) > 1:
            aliases = ", ".join(sorted(str(account.get("account_alias") or account.get("social_account_id") or "") for account in usable_matches))
            raise SocialAccountBindingError(
                f"Multiple social accounts assigned for task {task_name} ({platform}/{operational_agent_id}): {aliases}"
            )
        return usable_matches[0]

    def resolve_social_account(
        self,
        *,
        social_account_id: Optional[str] = None,
        account_alias: Optional[str] = None,
        tenant_id: str = "default",
        platform: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> ResolvedSocialAccount:
        """Resolve a social account and its login bundle for runtime use."""
        account = self.get_social_account(
            social_account_id=social_account_id,
            account_alias=account_alias,
            tenant_id=tenant_id,
            platform=platform,
            entity_id=entity_id,
        )
        login_alias = account.get("login_secret_alias_id")
        if not login_alias:
            raise SecretAliasNotFoundError(
                f"Social account {account.get('account_alias')} is missing a login secret alias"
            )
        login_value = self.resolve_alias(login_alias)
        mfa_alias = account.get("mfa_secret_alias_id")
        mfa_secret = self.resolve_alias(mfa_alias) if mfa_alias else None
        return ResolvedSocialAccount(
            social_account_id=account["social_account_id"],
            tenant_id=account["tenant_id"],
            platform=account["platform"],
            account_alias=account["account_alias"],
            entity_scope=account.get("entity_scope"),
            persona_scope=account.get("persona_scope"),
            state=account.get("state") or "",
            login_secret=login_value,
            mfa_secret=mfa_secret,
            login_secret_alias_id=login_alias,
            mfa_secret_alias_id=mfa_alias,
        )
