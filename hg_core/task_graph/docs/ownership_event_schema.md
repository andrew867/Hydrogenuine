# Ownership Event Schema (JSONL / DB row)

Common fields:
- ts, run_id, task_id, event_id, type, actor, expected_version (optional)

Types:

offer_ownership:
- token_id, to, lease_ttl_s, ack_deadline_ts, roles_delta

accept_ownership:
- token_id

decline_ownership:
- token_id, reason

renew_lease:
- token_id, new_expiry_ts

release_ownership:
- token_id, next_offer (optional)

set_pending_review:
- approver_spec, escalation_spec, sla_s, checkpoint_id

approve_review / deny_review:
- checkpoint_id, decision, comment (optional)

contested:
- claims: [{token_id, actor, ts}]

Events are stored in SQLite `ownership_events` table (and mirrored in FTS5 for search). Payload is JSON in payload column.
