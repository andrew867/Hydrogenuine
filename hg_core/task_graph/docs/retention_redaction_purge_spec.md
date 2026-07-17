# Spec: Retention, redaction, and purge

## Goal
Define what data is stored, for how long, and how sensitive information is removed.

## Artifact classes
- Run traces (structured execution records)
- Audit summaries (human readable)
- Dead-letter artifacts (replay inputs + errors)
- Approval decisions and requests
- Change proposals and canary results
- Output artifacts (generated content, derived reports)
- Knowledge ingestion artifacts (sources metadata and extracted facts)

## Retention policy buckets (suggested)
- Short: raw content and full payloads (days to weeks)
- Medium: traces, summaries, dead-letters (weeks to months)
- Long: hashes, counts, metrics rollups, provenance pointers (months+)

Exact durations are policy-controlled and can be tuned.

## Redaction requirements
- No secrets in any stored artifacts.
- Redact known patterns: keys, tokens, authorization headers.
- For outbound content, store:
  - hashes and minimal summaries
  - full content only when needed for audit and within retention rules.

## Purge/forget operations
- Purge by run_id
- Purge by date range and artifact class
- Purge by workflow_id
- Purge sensitive payloads while retaining non-sensitive metrics (tombstone records)

## Acceptance
- A purge operation removes targeted artifacts and records the action in an audit log.
- Redaction is tested with fixtures containing mock secrets.
