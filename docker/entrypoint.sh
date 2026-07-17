#!/bin/sh
set -e

echo "=== Hydrogenuine Agent Zero ==="
echo "Mode: ${HG_MODE:-fixture}"
echo "Profile: ${HG_RUNTIME_PROFILE:-fixture}"
echo "Remote providers disabled: ${HG_DISABLE_REMOTE_PROVIDERS:-true}"
echo "Live effects disabled: ${HG_DISABLE_LIVE_EFFECTS:-true}"
echo "Operator review required: ${HG_REQUIRE_OPERATOR_REVIEW:-true}"
echo "Model downloads allowed: ${HG_ALLOW_MODEL_DOWNLOADS:-false}"
echo "=== Safety Boundaries ==="
echo "Phase 19 remains YELLOW."
echo "Phase 24 remains infrastructure-only."
echo "Zero is not AGI. Zero is not conscious. Zero is not sovereign."
echo "Zero cannot self-authorize."
echo "==========================="

# Ensure data directories exist
mkdir -p "${HG_PROOF_DIR:-/data/proofs}" "${HG_REPORT_DIR:-/data/reports}" "${HG_STATE_DIR:-/data/state}"

exec "$@"
