"""Security utilities: redaction, secrets handling (Pack3); prompt-injection (Pack4); secrets provider (Pack6)."""

from hg_core.security.secrets_provider import (
    SecretsProvider,
    EnvSecretsProvider,
    VaultSecretsProvider,
    get_default_provider,
)
from hg_core.security.keystore import (
    KeystoreService,
    KeystoreError,
    SocialAccountBindingError,
    SecretAliasDisabledError,
    SecretAliasNotFoundError,
    SecretResolutionError,
    SocialAccountBinding,
    SocialAccountNotFoundError,
    SocialAccountStateError,
    ResolvedSocialAccount,
)
from hg_core.security.social_account_artifacts import (
    account_artifacts_root,
    get_latest_bound_browser_session_id,
    record_social_account_session_binding,
    record_social_account_artifact,
    register_social_account_artifact,
    write_social_account_artifact,
)
from hg_core.security.redaction import (
    redact_text,
    redact_json,
    SENSITIVE_KEYS,
)
from hg_core.security.prompt_injection import assess, InjectionAssessment
from hg_core.security.sanitizers import sanitize_for_rag, sanitize_for_memory_write

__all__ = [
    "SecretsProvider",
    "EnvSecretsProvider",
    "VaultSecretsProvider",
    "get_default_provider",
    "KeystoreService",
    "KeystoreError",
    "SocialAccountBindingError",
    "SecretAliasDisabledError",
    "SecretAliasNotFoundError",
    "SecretResolutionError",
    "SocialAccountBinding",
    "SocialAccountNotFoundError",
    "SocialAccountStateError",
    "ResolvedSocialAccount",
    "account_artifacts_root",
    "get_latest_bound_browser_session_id",
    "record_social_account_session_binding",
    "record_social_account_artifact",
    "register_social_account_artifact",
    "write_social_account_artifact",
    "redact_text",
    "redact_json",
    "SENSITIVE_KEYS",
    "assess",
    "InjectionAssessment",
    "sanitize_for_rag",
    "sanitize_for_memory_write",
]
