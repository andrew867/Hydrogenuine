"""CT-02 secret/credential safety — resolver, redaction, scanning."""

from hg_core.secrets.bundle import refuse_seal_if_leak, seal_proof_bundle
from hg_core.secrets.canary import (
    CANARY_ENV_NAMES,
    CANARY_MARKERS,
    all_canary_values,
    clear_canary_env,
    contains_canary,
    plant_canary_env,
)
from hg_core.secrets.crash import format_crash_report
from hg_core.secrets.events import SecretEmissionRefused, guard_event_payload
from hg_core.secrets.jail import JAIL_VIOLATION_CODE, check_ter_secret_jail
from hg_core.secrets.redact import (
    RedactionFailure,
    SecretLeakError,
    contains_leak,
    contains_raw_secret_pattern,
    redact_or_refuse,
    redact_payload,
    redact_text,
    refuse_if_leak,
)
from hg_core.secrets.resolver import SecretRefusal, SecretResolver, default_resolver
from hg_core.secrets.scan import manifest_hash, scan_directory, scan_file, scan_text

__all__ = [
    "CANARY_ENV_NAMES",
    "CANARY_MARKERS",
    "JAIL_VIOLATION_CODE",
    "RedactionFailure",
    "SecretEmissionRefused",
    "SecretLeakError",
    "SecretRefusal",
    "SecretResolver",
    "all_canary_values",
    "check_ter_secret_jail",
    "clear_canary_env",
    "contains_canary",
    "contains_leak",
    "contains_raw_secret_pattern",
    "default_resolver",
    "format_crash_report",
    "guard_event_payload",
    "manifest_hash",
    "plant_canary_env",
    "redact_or_refuse",
    "redact_payload",
    "redact_text",
    "refuse_if_leak",
    "refuse_seal_if_leak",
    "scan_directory",
    "scan_file",
    "scan_text",
    "seal_proof_bundle",
]
